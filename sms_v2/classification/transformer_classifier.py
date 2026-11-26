"""Fine-tuned transformer sequence classifier: MARBERT, AraBERT, XLM-RoBERTa.

One implementation for all three; they differ only in checkpoint and a few
hyperparameters (config.settings.TRANSFORMER_MODELS). The checkpoints are not
interchangeable — different vocabularies, casing and tokenizers — so each model
loads its OWN tokenizer from its own checkpoint and saves it next to its weights.

Training (manual loop, like sms_v2/marbert.py: torch + transformers only)
  * AdamW, linear warmup/decay, gradient clipping
  * class-weighted cross-entropy (inverse class frequency on TRAIN only)
  * fp16 autocast + GradScaler on CUDA (T4 has no bf16); fp32 on CPU
  * validation macro F1 after every epoch; early stopping on it
  * checkpoint after EVERY epoch:
        <work>/checkpoints/last/   weights + tokenizer + training_state.pt
                                   (optimizer, scheduler, scaler, RNG, history)
        <work>/checkpoints/best/   weights + tokenizer of the best epoch so far
  * resume: if checkpoints/last exists and its fingerprint (checkpoint name,
    hyperparameters, classes, preprocessing, training ids) matches, training
    continues from the next epoch with the same data order it would have had.
    A mismatching fingerprint is an error, never a silent restart.
  * optional second copy (checkpoint_backup.py, a Drive folder on Colab) pushed
    after every epoch; on resume the newest copy that verifies wins, local or
    backup, falling back slot by slot. A failed backup is logged, not fatal.

The test set never reaches this file.
"""
import gc
import hashlib
import json
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from classification.base_classifier import (BaseClassifier, check_preprocessing,  # noqa: E402
                                            read_meta)
from config import settings as S                                                # noqa: E402


def _torch():
    try:
        import torch
        import transformers                                           # noqa: F401
        return torch
    except ImportError as e:
        raise SystemExit("transformer models need torch and transformers:\n"
                         "    pip install -q transformers   (Colab already has torch)") from e


def pick_device(requested="auto"):
    torch = _torch()
    if requested and requested != "auto":
        return torch.device(requested)
    if torch.cuda.is_available():
        return torch.device("cuda")
    return torch.device("cpu")


def set_seed(seed):
    import random
    torch = _torch()
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)


def _atomic_dir_replace(tmp, final):
    """Swap a fully-written tmp dir into place. A crash leaves either old or new."""
    old = final + ".old"
    if os.path.isdir(old):
        shutil.rmtree(old)
    if os.path.isdir(final):
        os.replace(final, old)
    os.replace(tmp, final)
    if os.path.isdir(old):
        shutil.rmtree(old, ignore_errors=True)


class TransformerClassifier(BaseClassifier):
    family = "transformer"
    score_type = "probability"
    supports_proba = True

    def __init__(self, classes, model_key, checkpoint, device="auto", **hp):
        cfg = dict(S.TRANSFORMER_DEFAULTS)
        cfg.update({k: v for k, v in hp.items() if k in S.TRANSFORMER_DEFAULTS})
        rest = {k: v for k, v in hp.items() if k not in S.TRANSFORMER_DEFAULTS}
        super().__init__(classes, **rest)
        self.name = model_key
        self.checkpoint = checkpoint
        self.cfg = cfg
        self.device_req = device
        self.model = self.tok = None
        self.params.update(checkpoint=checkpoint, **cfg)

    # ------------------------------------------------------------ building
    def _build(self, source, pretrained=False):
        """pretrained=True when starting from the hub checkpoint: a classification
        head of the wrong size there (some checkpoints ship one) is re-initialised.
        Our own checkpoints must match exactly, so the flag is off for them."""
        from transformers import AutoModelForSequenceClassification, AutoTokenizer
        tok = AutoTokenizer.from_pretrained(source, use_fast=True)
        model = AutoModelForSequenceClassification.from_pretrained(
            source, num_labels=len(self.classes),
            id2label=dict(enumerate(self.classes)),
            label2id={c: i for i, c in enumerate(self.classes)},
            ignore_mismatched_sizes=pretrained)
        return model, tok

    def _encode(self, texts):
        return self.tok(texts, truncation=True, max_length=self.cfg["max_len"],
                        padding=False)["input_ids"]

    def _collate(self, rows):
        torch = _torch()
        width = max(len(r) for r in rows)
        pad = self.tok.pad_token_id
        ids = torch.tensor([r + [pad] * (width - len(r)) for r in rows], dtype=torch.long)
        mask = torch.tensor([[1] * len(r) + [0] * (width - len(r)) for r in rows],
                            dtype=torch.long)
        return ids, mask

    def fingerprint(self, train_ids):
        blob = json.dumps({"checkpoint": self.checkpoint, "cfg": self.cfg,
                           "classes": self.classes, "pre": self.preprocessing,
                           "train": list(train_ids)}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    # ------------------------------------------------------------ training
    def train(self, train_texts, train_labels, val_texts=None, val_labels=None,
              work_dir=None, train_ids=None, resume=True, log=print, backup=None, **kw):
        """backup: an optional classification.checkpoint_backup.CheckpointBackup that
        receives a copy of the state after every epoch and is consulted on resume."""
        torch = _torch()
        from sklearn.metrics import f1_score
        from torch.optim import AdamW
        from transformers import get_linear_schedule_with_warmup

        if work_dir is None:
            raise ValueError("work_dir is required: checkpoints have to live somewhere")
        if val_texts is None:
            raise ValueError("a validation set is required for early stopping")
        cfg = self.cfg
        dev = pick_device(self.device_req)
        use_amp = bool(cfg["fp16"]) and dev.type == "cuda"
        ck_last = os.path.join(work_dir, "checkpoints", "last")
        ck_best = os.path.join(work_dir, "checkpoints", "best")
        fp = self.fingerprint(train_ids if train_ids is not None else train_texts)

        state, resumed_from, backup_errors = None, None, []
        if resume:
            state, resumed_from = self._resume_state(ck_last, ck_best, fp, backup, log)
        if state is not None:
            log(f"  resuming {self.name} after epoch {state['epoch']} ({resumed_from})")
            self.model, self.tok = self._build(ck_last)
        else:
            set_seed(cfg["seed"])
            self.model, self.tok = self._build(self.checkpoint, pretrained=True)
        self.model.to(dev)

        lab2id = {c: i for i, c in enumerate(self.classes)}
        tr_ids = self._encode(self.prepare(train_texts))
        tr_y = np.array([lab2id[y] for y in train_labels])
        va_ids = self._encode(self.prepare(val_texts))
        va_y = [lab2id[y] for y in val_labels]

        counts = np.bincount(tr_y, minlength=len(self.classes)).astype(float)
        if cfg["class_weighting"] == "balanced":
            w = np.where(counts > 0, counts.sum() / (len(self.classes) * np.maximum(counts, 1)), 0.0)
        else:
            w = np.ones(len(self.classes))
        loss_fn = torch.nn.CrossEntropyLoss(weight=torch.tensor(w, dtype=torch.float32, device=dev))

        bs = cfg["batch_size"]
        steps_per_epoch = int(np.ceil(len(tr_ids) / bs))
        total = steps_per_epoch * cfg["epochs"]
        no_decay = ("bias", "LayerNorm.weight", "layer_norm.weight")
        groups = [{"params": [p for n, p in self.model.named_parameters()
                              if not any(nd in n for nd in no_decay)],
                   "weight_decay": cfg["weight_decay"]},
                  {"params": [p for n, p in self.model.named_parameters()
                              if any(nd in n for nd in no_decay)],
                   "weight_decay": 0.0}]
        opt = AdamW(groups, lr=cfg["lr"])
        sched = get_linear_schedule_with_warmup(opt, int(total * cfg["warmup_ratio"]), total)
        scaler = _grad_scaler(torch, use_amp)

        history, start_epoch = [], 0
        best_f1, best_epoch, bad_epochs, stopped = -1.0, 0, 0, False
        train_time = 0.0
        if state is not None:
            opt.load_state_dict(state["optimizer"])
            sched.load_state_dict(state["scheduler"])
            if use_amp and state.get("scaler"):
                scaler.load_state_dict(state["scaler"])
            history = state["history"]
            start_epoch = state["epoch"]
            best_f1, best_epoch = state["best_f1"], state["best_epoch"]
            bad_epochs, stopped = state["bad_epochs"], state["stopped"]
            train_time = state.get("train_time_s", 0.0)
            _restore_rng(torch, state["rng"])

        if dev.type == "cuda":
            torch.cuda.reset_peak_memory_stats()

        for epoch in range(start_epoch, cfg["epochs"]):
            if stopped:
                break
            t0 = time.perf_counter()
            self.model.train()
            order = np.random.default_rng(cfg["seed"] + epoch).permutation(len(tr_ids))
            running = 0.0
            for b in range(steps_per_epoch):
                sel = order[b * bs:(b + 1) * bs]
                ids, mask = self._collate([tr_ids[i] for i in sel])
                ids, mask = ids.to(dev), mask.to(dev)
                y = torch.tensor(tr_y[sel], dtype=torch.long, device=dev)
                with torch.autocast(device_type=dev.type, dtype=torch.float16, enabled=use_amp):
                    logits = self.model(input_ids=ids, attention_mask=mask).logits
                loss = loss_fn(logits.float(), y)
                scaler.scale(loss).backward()
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), cfg["grad_clip"])
                scaler.step(opt)
                scaler.update()
                sched.step()
                opt.zero_grad(set_to_none=True)
                running += loss.item()
                if (b + 1) % 20 == 0 or b + 1 == steps_per_epoch:
                    log(f"  {self.name} epoch {epoch + 1}/{cfg['epochs']} "
                        f"step {b + 1}/{steps_per_epoch} loss {running / (b + 1):.4f}")
            epoch_time = time.perf_counter() - t0
            train_time += epoch_time

            va_prob = self._predict_ids(va_ids, dev, use_amp)
            va_pred = va_prob.argmax(1)
            va_f1 = float(f1_score(va_y, va_pred, labels=list(range(len(self.classes))),
                                   average="macro", zero_division=0))
            va_loss = float(-np.mean(np.log(np.clip(va_prob[np.arange(len(va_y)), va_y], 1e-12, 1))))
            improved = va_f1 > best_f1 + 1e-6
            if improved:
                best_f1, best_epoch, bad_epochs = va_f1, epoch + 1, 0
            else:
                bad_epochs += 1
            stopped = bad_epochs >= cfg["early_stopping_patience"]
            history.append({"epoch": epoch + 1, "train_loss": running / steps_per_epoch,
                            "val_loss": va_loss, "val_macro_f1": va_f1,
                            "epoch_time_s": epoch_time, "improved": improved})
            log(f"  {self.name} epoch {epoch + 1}: val macro-F1 {va_f1:.4f} "
                f"(best {best_f1:.4f} @ {best_epoch}) {epoch_time:.0f}s"
                + ("  -> early stop" if stopped else ""))

            if improved:
                self._save_weights(ck_best)
            self._save_weights(ck_last, training_state={
                "fingerprint": fp, "epoch": epoch + 1, "optimizer": opt.state_dict(),
                "scheduler": sched.state_dict(),
                "scaler": scaler.state_dict() if use_amp else None,
                "history": history, "best_f1": best_f1, "best_epoch": best_epoch,
                "bad_epochs": bad_epochs, "stopped": stopped, "train_time_s": train_time,
                "rng": _rng_state(torch)})
            if backup is not None:
                last_epoch = stopped or epoch + 1 == cfg["epochs"]
                t1 = time.perf_counter()
                try:
                    slot = backup.push(fp, epoch + 1, best_epoch, ck_last, ck_best,
                                       force=last_epoch)
                    if slot is not None:
                        log(f"  {self.name} epoch {epoch + 1}: backed up to slot_{slot} "
                            f"({time.perf_counter() - t1:.0f}s)")
                except OSError as e:        # e.g. Drive full: keep training, say so loudly
                    backup_errors.append(f"epoch {epoch + 1}: {type(e).__name__}: {e}")
                    log(f"  !! {self.name} epoch {epoch + 1}: BACKUP FAILED ({e}); training "
                        "continues, but a lost VM would restart this run")

        peak = torch.cuda.max_memory_allocated() / 2 ** 20 if dev.type == "cuda" else None
        # finish on the BEST epoch's weights, not the last one's
        self.release()
        self.model, self.tok = self._build(ck_best)
        self.model.to(dev).eval()
        self.train_info = {"train_time_s": train_time, "best_epoch": best_epoch,
                           "best_val_macro_f1": best_f1, "epochs_run": len(history),
                           "early_stopped": stopped, "history": history,
                           "device": str(dev), "fp16": use_amp,
                           "peak_gpu_mem_train_mb": peak, "n_train": len(tr_ids),
                           "fingerprint": fp, "resumed_from": resumed_from,
                           "backup_errors": backup_errors}
        return self.train_info

    def _resume_state(self, ck_last, ck_best, fp, backup, log):
        """Newest usable training state: the local checkpoint, or a backup slot that is
        newer and verifies. -> (state | None, description | None)."""
        torch = _torch()
        path = os.path.join(ck_last, "training_state.pt")

        def read_local():
            if not (os.path.exists(path) and os.path.isdir(ck_best)):
                return None
            try:
                return torch.load(path, map_location="cpu", weights_only=False)
            except Exception as e:                      # truncated file, etc.
                log(f"  local checkpoint {ck_last} unreadable ({type(e).__name__}); ignoring it")
                return None

        state = read_local()
        if state is not None and state["fingerprint"] != fp:
            raise RuntimeError(
                f"{ck_last} belongs to a different configuration (fingerprint "
                f"{state['fingerprint']} != {fp}). Delete it or run with --overwrite.")
        source = "local checkpoint" if state is not None else None
        if backup is None:
            return state, source
        have = state["epoch"] if state is not None else 0
        for i in backup.candidates(fp):
            epoch = backup.manifest(i).get("epoch", 0)
            if epoch <= have:
                break
            try:
                backup.restore(i, ck_last, ck_best)       # leaves local dirs alone on failure
            except Exception as e:
                log(f"  backup slot_{i} (epoch {epoch}) unusable: {e}; trying the next one")
                continue
            restored = read_local()
            if restored is not None and restored["fingerprint"] == fp \
                    and restored["epoch"] == epoch:
                return restored, f"backup slot_{i}"
            # verified bytes but not the state the manifest promised: the local copy
            # is overwritten now, so only an older slot or a fresh start remains
            log(f"  backup slot_{i} restored but its state does not match its manifest")
            state, source, have = None, None, 0
        if state is None:
            for d in (ck_last, ck_best):
                shutil.rmtree(d, ignore_errors=True)
        return state, source

    def _save_weights(self, directory, training_state=None):
        torch = _torch()
        tmp = directory + ".tmp"
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        os.makedirs(tmp)
        self.model.save_pretrained(tmp)
        self.tok.save_pretrained(tmp)
        if training_state is not None:
            torch.save(training_state, os.path.join(tmp, "training_state.pt"))
        _atomic_dir_replace(tmp, directory)

    # ------------------------------------------------------------ inference
    def _predict_ids(self, id_rows, dev, use_amp):
        torch = _torch()
        self.model.eval()
        order = np.argsort([len(r) for r in id_rows])       # length-sorted = less padding
        out = np.zeros((len(id_rows), len(self.classes)), dtype=np.float32)
        bs = self.cfg["eval_batch_size"]
        with torch.no_grad():
            for i in range(0, len(order), bs):
                sel = order[i:i + bs]
                ids, mask = self._collate([id_rows[j] for j in sel])
                with torch.autocast(device_type=dev.type, dtype=torch.float16, enabled=use_amp):
                    logits = self.model(input_ids=ids.to(dev), attention_mask=mask.to(dev)).logits
                out[sel] = torch.softmax(logits.float(), dim=-1).cpu().numpy()
        return out

    def _scores(self, prepared):
        if not prepared:
            return np.zeros((0, len(self.classes)))
        dev = next(self.model.parameters()).device
        use_amp = bool(self.cfg["fp16"]) and dev.type == "cuda"
        return self._predict_ids(self._encode(prepared), dev, use_amp)

    # ------------------------------------------------------------ persistence
    def save(self, directory):
        tmp = directory + ".tmp"
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        os.makedirs(tmp)
        self.model.save_pretrained(tmp)
        self.tok.save_pretrained(tmp)
        self.write_meta(tmp)
        _atomic_dir_replace(tmp, directory)

    def meta(self):
        m = super().meta()
        m.update(model_key=self.name, checkpoint=self.checkpoint, cfg=self.cfg)
        return m

    @classmethod
    def load(cls, directory, device="auto"):
        meta = read_meta(directory)
        check_preprocessing(meta)
        obj = cls(meta["classes"], meta["model_key"], meta["checkpoint"], device=device,
                  threshold=meta.get("threshold"), **meta["cfg"])
        obj.train_info = meta.get("train_info", {})
        obj.model, obj.tok = obj._build(directory)
        obj.model.to(pick_device(device)).eval()
        return obj

    def release(self):
        torch = _torch()
        self.model = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


# ------------------------------------------------------------------ helpers
def _grad_scaler(torch, enabled):
    try:
        return torch.amp.GradScaler("cuda", enabled=enabled)
    except (AttributeError, TypeError):                     # torch < 2.3
        return torch.cuda.amp.GradScaler(enabled=enabled)


def _rng_state(torch):
    import random
    st = {"python": random.getstate(), "numpy": np.random.get_state(),
          "torch": torch.get_rng_state()}
    if torch.cuda.is_available():
        st["cuda"] = torch.cuda.get_rng_state_all()
    return st


def _restore_rng(torch, st):
    import random
    random.setstate(st["python"])
    np.random.set_state(st["numpy"])
    torch.set_rng_state(st["torch"])
    if "cuda" in st and torch.cuda.is_available():
        torch.cuda.set_rng_state_all(st["cuda"])
