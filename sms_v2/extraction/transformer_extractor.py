"""Transformer Stage-2 extractor (Experiment 1) and joint classifier+extractor (Experiment 2).

Architecture: sms_v2/marbert.py's extractor, reused as is (marbert.build_extractor):

    encoder (MARBERT or AraBERT)
      ├─ token head    BIO over AMOUNT/FEE/BALANCE/LAST4/MERCHANT/CURRENCY/DATE/TIME (17)
      ├─ type head     debit, credit, transfer_out, transfer_in, atm_withdrawal, bill_payment, other
      └─ channel head  card, instapay, wallet, bank_transfer, atm, other, unknown
    loss = plain sum of the three cross-entropies

Decoding is sms_v2/pipeline.py's Pipeline._assemble, reused as is: a transaction must
carry an amount, "no fees" in words -> fee 0, DATE/TIME spans parsed by spans.py,
currency falls back to the nearest currency token. Its v1-schema record is turned into
the benchmark's output record by extraction.base.from_v1, exactly like the v1 extractor.

JointModel (Experiment 2) adds ONE head on the same pooled [CLS] vector: the Stage-1
label (binary or 6-class, the existing gold labels, no new classes). One forward pass
gives the class AND the fields. Loss = class-weighted CE (as the classifiers) + the
three extraction losses, the extraction losses computed on gold transactions only
(non-transactions have no field labels, exactly as the separate extractor never sees
them). So the only difference from Experiment 1 is that one encoder is shared.

What is new compared with the original marbert.py/train.py (and why):
  * benchmark train/val/test split instead of dataset.py's 80/20 split (which overlaps
    the benchmark's test set);
  * early stopping on validation (extractor: full-record exact on gold val
    transactions; joint: mean of that and val macro-F1);
  * the classifiers' per-epoch checkpoints, fingerprinted resume and Drive backup
    (TransformerClassifier._resume_state is reused, not copied);
  * the encoder reads spans.normalize(text) (= the benchmark's "digits" preprocessing,
    length-preserving, so offsets stay valid in the raw text).

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
import marbert                                                              # noqa: E402
import pipeline as v2pipe                                                   # noqa: E402
import spans                                                                # noqa: E402
from classification.base_classifier import BaseClassifier                   # noqa: E402
from classification.transformer_classifier import (TransformerClassifier,   # noqa: E402
                                                   _atomic_dir_replace, _grad_scaler,
                                                   _restore_rng, _rng_state, _torch,
                                                   pick_device, set_seed)
from config import labels as L                                              # noqa: E402
from config import settings as S                                            # noqa: E402
from dataset import bio_from_spans, decode_bio                              # noqa: E402
from evaluation import extraction_metrics as EM                             # noqa: E402
from extraction.base import BaseExtractor, from_v1, to_v1                   # noqa: E402
from schema import CHANNELS, IGNORE_INDEX, TOKEN_LABELS, TYPES              # noqa: E402

META = "extractor.json"
# The encoder input. Fixed (not S.PREPROCESSING): spans need a length-preserving view.
INPUT_PREPROCESSING = "digits"
ID2LABEL = dict(enumerate(TOKEN_LABELS))


def is_transformer_extractor_dir(directory):
    return os.path.exists(os.path.join(directory, META))


def _forward(net, ids, mask):
    """marbert.py's Extractor.forward, plus the optional classification head."""
    out = net.encoder(input_ids=ids, attention_mask=mask)
    seq = net.dropout(out.last_hidden_state)
    pooled = net.dropout(out.last_hidden_state[:, 0])
    cls = net.cls_head(pooled) if hasattr(net, "cls_head") else None
    return net.token_head(seq), net.type_head(pooled), net.channel_head(pooled), cls


class TransformerExtractor(BaseExtractor):
    family = "transformer_extractor"
    score_type = "probability"
    supports_proba = True

    # resume logic shared with the classifiers (it uses no instance state)
    _resume_state = TransformerClassifier._resume_state

    def __init__(self, model_key, checkpoint, classes=None, device="auto", threshold=None, **hp):
        cfg = dict(S.TRANSFORMER_DEFAULTS)
        cfg.update(S.EXTRACTOR_DEFAULTS)
        unknown = sorted(set(hp) - set(cfg))
        if unknown:
            raise ValueError(f"unknown hyperparameter(s) {unknown}; known: {sorted(cfg)}")
        cfg.update(hp)
        if classes is not None and L.TRANSACTION not in classes:
            raise ValueError(f"classes must include {L.TRANSACTION!r}")
        self.name = model_key
        self.checkpoint = checkpoint
        self.classes = list(classes) if classes is not None else None
        self.cfg = cfg
        self.device_req = device
        self.threshold = threshold
        self.preprocessing = INPUT_PREPROCESSING
        self.net = self.tok = None
        self.train_info = {}
        self.fit_time_s = None

    @property
    def is_joint(self):
        return self.classes is not None

    # ------------------------------------------------------------ building
    def _attach_cls_head(self, net):
        if self.is_joint:
            import torch.nn as nn
            net.cls_head = nn.Linear(net.encoder.config.hidden_size, len(self.classes))
        return net

    def _build_pretrained(self):
        net = self._attach_cls_head(marbert.build_extractor(self.checkpoint, self.cfg["dropout"]))
        return net, marbert.load_tokenizer(self.checkpoint)

    def _load_weights(self, directory):
        torch = _torch()
        net = self._attach_cls_head(
            marbert.build_extractor(os.path.join(directory, "encoder"), self.cfg["dropout"]))
        heads = torch.load(os.path.join(directory, "heads.pt"), map_location="cpu")
        missing, unexpected = net.load_state_dict(heads, strict=False)
        missing = [k for k in missing if not k.startswith("encoder.")]
        if missing or unexpected:
            raise RuntimeError(f"{directory}: heads do not match this model "
                               f"(missing {missing}, unexpected {unexpected})")
        return net, marbert.load_tokenizer(directory)

    def _save_weights(self, directory, training_state=None, meta=None):
        torch = _torch()
        tmp = directory + ".tmp"
        if os.path.isdir(tmp):
            shutil.rmtree(tmp)
        os.makedirs(tmp)
        self.net.encoder.save_pretrained(os.path.join(tmp, "encoder"))
        torch.save({k: v for k, v in self.net.state_dict().items()
                    if not k.startswith("encoder.")}, os.path.join(tmp, "heads.pt"))
        self.tok.save_pretrained(tmp)
        if training_state is not None:
            torch.save(training_state, os.path.join(tmp, "training_state.pt"))
        if meta is not None:
            with open(os.path.join(tmp, META), "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=1, default=str)
        _atomic_dir_replace(tmp, directory)

    def fingerprint(self, train_ids, label_col):
        blob = json.dumps({"kind": self.family, "checkpoint": self.checkpoint, "cfg": self.cfg,
                           "classes": self.classes, "label": label_col,
                           "pre": self.preprocessing, "train": list(train_ids)}, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:16]

    # ------------------------------------------------------------ data
    def _rows(self, records, label_col):
        lab2id = {c: i for i, c in enumerate(self.classes or [])}
        rows, skipped = [], 0
        for r in records:
            raw = r.get("sms") or ""
            enc = self.tok(spans.normalize(raw), truncation=True, max_length=self.cfg["max_len"],
                           return_offsets_mapping=True, return_special_tokens_mask=True)
            exp = r["expected"]
            n = len(enc["input_ids"])
            if exp["is_transaction"]:
                gold = spans.gold_spans(spans.bmp(raw), exp)
                tl = bio_from_spans(enc["offset_mapping"], gold, enc["special_tokens_mask"])
                ty = TYPES.index(exp["type"]) if exp.get("type") in TYPES else IGNORE_INDEX
                ch = CHANNELS.index(exp["channel"]) if exp.get("channel") in CHANNELS else IGNORE_INDEX
                skipped += ty == IGNORE_INDEX or ch == IGNORE_INDEX
            else:
                tl, ty, ch = [IGNORE_INDEX] * n, IGNORE_INDEX, IGNORE_INDEX
            y = lab2id[r[label_col]] if self.is_joint else -1
            rows.append((enc["input_ids"], tl, ty, ch, y))
        return rows, skipped

    def _collate(self, rows):
        torch = _torch()
        width = max(len(r[0]) for r in rows)
        pad = self.tok.pad_token_id
        ids = torch.tensor([r[0] + [pad] * (width - len(r[0])) for r in rows], dtype=torch.long)
        mask = torch.tensor([[1] * len(r[0]) + [0] * (width - len(r[0])) for r in rows],
                            dtype=torch.long)
        tl = torch.tensor([r[1] + [IGNORE_INDEX] * (width - len(r[1])) for r in rows],
                          dtype=torch.long)
        ty = torch.tensor([r[2] for r in rows], dtype=torch.long)
        ch = torch.tensor([r[3] for r in rows], dtype=torch.long)
        y = torch.tensor([r[4] for r in rows], dtype=torch.long)
        return ids, mask, tl, ty, ch, y

    # ------------------------------------------------------------ training
    def train(self, train_records, val_records, work_dir, label_col=None, resume=True,
              log=print, backup=None):
        """Extractor: uses only the GOLD TRANSACTIONS of train/val. Joint: every message,
        with `label_col` ("label_binary" / "label_multi") as the class target."""
        torch = _torch()
        import torch.nn.functional as F
        from torch.optim import AdamW
        from transformers import get_linear_schedule_with_warmup

        if self.is_joint and label_col is None:
            raise ValueError("a joint model needs label_col")
        if not self.is_joint:
            train_records = [r for r in train_records if r["expected"]["is_transaction"]]
            val_records = [r for r in val_records if r["expected"]["is_transaction"]]
        if not val_records:
            raise ValueError("a validation set is required for early stopping")
        cfg = self.cfg
        dev = pick_device(self.device_req)
        use_amp = bool(cfg["fp16"]) and dev.type == "cuda"
        ck_last = os.path.join(work_dir, "checkpoints", "last")
        ck_best = os.path.join(work_dir, "checkpoints", "best")
        fp = self.fingerprint([r["id"] for r in train_records], label_col)

        state, resumed_from, backup_errors = None, None, []
        if resume:
            state, resumed_from = self._resume_state(ck_last, ck_best, fp, backup, log)
        if state is not None:
            log(f"  resuming {self.name} after epoch {state['epoch']} ({resumed_from})")
            self.net, self.tok = self._load_weights(ck_last)
        else:
            set_seed(cfg["seed"])
            self.net, self.tok = self._build_pretrained()
        self.net.to(dev)

        tr_rows, skipped = self._rows(train_records, label_col)
        if skipped:
            log(f"  {skipped} training transactions have an out-of-schema type/channel "
                "(that head ignores them)")
        cls_w = None
        if self.is_joint:
            counts = np.bincount([r[4] for r in tr_rows], minlength=len(self.classes)).astype(float)
            if cfg["class_weighting"] == "balanced":
                w = np.where(counts > 0,
                             counts.sum() / (len(self.classes) * np.maximum(counts, 1)), 0.0)
            else:
                w = np.ones(len(self.classes))
            cls_w = torch.tensor(w, dtype=torch.float32, device=dev)

        def ce(logits, target, weight=None):
            if not bool((target != IGNORE_INDEX).any()):
                return logits.float().sum() * 0.0
            return F.cross_entropy(logits.float(), target, weight=weight, ignore_index=IGNORE_INDEX)

        bs = cfg["batch_size"]
        steps_per_epoch = int(np.ceil(len(tr_rows) / bs))
        total = steps_per_epoch * cfg["epochs"]
        no_decay = ("bias", "LayerNorm.weight", "layer_norm.weight")
        groups = [{"params": [p for n, p in self.net.named_parameters()
                              if not any(nd in n for nd in no_decay)],
                   "weight_decay": cfg["weight_decay"]},
                  {"params": [p for n, p in self.net.named_parameters()
                              if any(nd in n for nd in no_decay)],
                   "weight_decay": 0.0}]
        opt = AdamW(groups, lr=cfg["lr"])
        sched = get_linear_schedule_with_warmup(opt, int(total * cfg["warmup_ratio"]), total)
        scaler = _grad_scaler(torch, use_amp)

        history, start_epoch = [], 0
        best, best_epoch, bad_epochs, stopped, train_time = -1.0, 0, 0, False, 0.0
        if state is not None:
            opt.load_state_dict(state["optimizer"])
            sched.load_state_dict(state["scheduler"])
            if use_amp and state.get("scaler"):
                scaler.load_state_dict(state["scaler"])
            history, start_epoch = state["history"], state["epoch"]
            best, best_epoch = state["best_f1"], state["best_epoch"]
            bad_epochs, stopped = state["bad_epochs"], state["stopped"]
            train_time = state.get("train_time_s", 0.0)
            _restore_rng(torch, state["rng"])
        if dev.type == "cuda":
            torch.cuda.reset_peak_memory_stats()

        for epoch in range(start_epoch, cfg["epochs"]):
            if stopped:
                break
            t0 = time.perf_counter()
            self.net.train()
            order = np.random.default_rng(cfg["seed"] + epoch).permutation(len(tr_rows))
            running = 0.0
            for b in range(steps_per_epoch):
                sel = order[b * bs:(b + 1) * bs]
                ids, mask, tl, ty, ch, y = (t.to(dev) for t in self._collate([tr_rows[i] for i in sel]))
                with torch.autocast(device_type=dev.type, dtype=torch.float16, enabled=use_amp):
                    tok_l, ty_l, ch_l, cls_l = _forward(self.net, ids, mask)
                loss = (ce(tok_l.reshape(-1, tok_l.size(-1)), tl.reshape(-1))
                        + ce(ty_l, ty) + ce(ch_l, ch))
                if cls_l is not None:
                    loss = loss + F.cross_entropy(cls_l.float(), y, weight=cls_w)
                scaler.scale(loss).backward()
                scaler.unscale_(opt)
                torch.nn.utils.clip_grad_norm_(self.net.parameters(), cfg["grad_clip"])
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

            score, parts = self.selection_score(val_records, label_col)
            improved = score > best + 1e-6
            if improved:
                best, best_epoch, bad_epochs = score, epoch + 1, 0
            else:
                bad_epochs += 1
            stopped = bad_epochs >= cfg["early_stopping_patience"]
            history.append({"epoch": epoch + 1, "train_loss": running / steps_per_epoch,
                            "val_selection": score, **parts, "epoch_time_s": epoch_time,
                            "improved": improved})
            log(f"  {self.name} epoch {epoch + 1}: val selection {score:.4f} {parts} "
                f"(best {best:.4f} @ {best_epoch}) {epoch_time:.0f}s"
                + ("  -> early stop" if stopped else ""))

            if improved:
                self._save_weights(ck_best)
            self._save_weights(ck_last, training_state={
                "fingerprint": fp, "epoch": epoch + 1, "optimizer": opt.state_dict(),
                "scheduler": sched.state_dict(),
                "scaler": scaler.state_dict() if use_amp else None,
                "history": history, "best_f1": best, "best_epoch": best_epoch,
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
                except OSError as e:
                    backup_errors.append(f"epoch {epoch + 1}: {type(e).__name__}: {e}")
                    log(f"  !! {self.name} epoch {epoch + 1}: BACKUP FAILED ({e}); training "
                        "continues, but a lost VM would restart this run")

        peak = torch.cuda.max_memory_allocated() / 2 ** 20 if dev.type == "cuda" else None
        self.release()
        self.net, self.tok = self._load_weights(ck_best)       # the BEST epoch, not the last
        self.net.to(dev).eval()
        self.fit_time_s = train_time
        self.train_info = {"train_time_s": train_time, "best_epoch": best_epoch,
                           "best_val_selection": best, "selection": self.selection_rule(),
                           "epochs_run": len(history), "early_stopped": stopped,
                           "history": history, "device": str(dev), "fp16": use_amp,
                           "peak_gpu_mem_train_mb": peak, "n_train": len(tr_rows),
                           "n_val": len(val_records), "fingerprint": fp,
                           "resumed_from": resumed_from, "backup_errors": backup_errors}
        return self.train_info

    def selection_rule(self):
        if self.is_joint:
            return "mean(val macro-F1, val full-record exact on gold transactions)"
        return "val full-record exact on gold transactions"

    def selection_score(self, val_records, label_col):
        labels, _, outs = self.infer([r["sms"] for r in val_records])
        pairs = [(r["expected"], to_v1(o) if o["extraction_ok"] else None)
                 for r, o in zip(val_records, outs) if r["expected"]["is_transaction"]]
        ext = EM.field_scores(pairs)["full_record_exact"] or 0.0
        if not self.is_joint:
            return ext, {"val_full_record_exact": ext}
        from sklearn.metrics import f1_score
        f1 = float(f1_score([r[label_col] for r in val_records], labels, labels=self.classes,
                            average="macro", zero_division=0))
        return 0.5 * (f1 + ext), {"val_macro_f1": f1, "val_full_record_exact": ext}

    # ------------------------------------------------------------ inference
    def infer(self, texts):
        """ONE forward pass per batch -> (labels | None, class probabilities | None,
        output records). Labels/probabilities only for a joint model."""
        torch = _torch()
        texts = [t if isinstance(t, str) else ("" if t is None else str(t)) for t in texts]
        n = len(texts)
        k = len(self.classes) if self.is_joint else 0
        probs = np.zeros((n, k), dtype=np.float32) if self.is_joint else None
        outs = [None] * n
        if n == 0:
            return ([] if self.is_joint else None), probs, outs
        dev = next(self.net.parameters()).device
        use_amp = bool(self.cfg["fp16"]) and dev.type == "cuda"
        norm = [spans.normalize(t) for t in texts]
        order = np.argsort([len(t) for t in norm], kind="stable")
        bs = self.cfg["eval_batch_size"]
        self.net.eval()
        with torch.no_grad():
            for i in range(0, n, bs):
                sel = order[i:i + bs]
                enc = self.tok([norm[j] for j in sel], truncation=True,
                               max_length=self.cfg["max_len"], padding=True,
                               return_offsets_mapping=True, return_tensors="pt")
                offsets = enc["offset_mapping"]
                mask = enc["attention_mask"]
                with torch.autocast(device_type=dev.type, dtype=torch.float16, enabled=use_amp):
                    tok_l, ty_l, ch_l, cls_l = _forward(self.net, enc["input_ids"].to(dev),
                                                        mask.to(dev))
                tok_ids = tok_l.argmax(-1).cpu()
                types = ty_l.argmax(-1).cpu()
                chans = ch_l.argmax(-1).cpu()
                if cls_l is not None:
                    probs[sel] = torch.softmax(cls_l.float(), dim=-1).cpu().numpy()
                for b, j in enumerate(sel):
                    m = int(mask[b].sum())
                    offs = [tuple(map(int, o)) for o in offsets[b][:m]]
                    text_b = spans.bmp(texts[j])
                    found = decode_bio(offs, tok_ids[b][:m].tolist(), text_b, ID2LABEL)
                    got = ({t: text_b[s:e] for t, (s, e) in found.items()}, found,
                           TYPES[int(types[b])], CHANNELS[int(chans[b])])
                    try:
                        rec = v2pipe.Pipeline._assemble(None, texts[j], got, None)
                    except Exception as e:          # never let one odd SMS kill a batch
                        rec = {"is_transaction": False, "_reason": f"extractor error: {e}"}
                    outs[j] = from_v1(rec, norm[j])
        labels = self.labels_from_scores(probs) if self.is_joint else None
        return labels, probs, outs

    def extract_many(self, texts):
        return self.infer(texts)[2]

    # BaseClassifier-compatible part (joint models only)
    def labels_from_scores(self, scores):
        return BaseClassifier.labels_from_scores(self, scores)

    def predict_with_scores(self, texts):
        if not self.is_joint:
            raise TypeError(f"{self.name} is an extractor, not a classifier")
        labels, probs, _ = self.infer(texts)
        return labels, probs

    def predict(self, texts):
        return self.predict_with_scores(texts)[0]

    def n_parameters(self):
        return int(sum(p.numel() for p in self.net.parameters())) if self.net is not None else None

    # ------------------------------------------------------------ persistence
    def meta(self):
        return {"name": self.name, "family": self.family, "model_key": self.name,
                "checkpoint": self.checkpoint, "classes": self.classes, "cfg": self.cfg,
                "threshold": self.threshold, "preprocessing": self.preprocessing,
                "token_labels": TOKEN_LABELS, "types": TYPES, "channels": CHANNELS,
                "train_info": self.train_info}

    def save(self, directory):
        self._save_weights(directory, meta=self.meta())

    @classmethod
    def load(cls, directory, device="auto"):
        path = os.path.join(directory, META)
        if not os.path.exists(path):
            raise FileNotFoundError(f"{directory} holds no trained transformer extractor "
                                    f"({META} missing)")
        with open(path, encoding="utf-8") as f:
            meta = json.load(f)
        if meta.get("token_labels") != TOKEN_LABELS or meta.get("types") != TYPES \
                or meta.get("channels") != CHANNELS:
            raise ValueError(f"{directory}: label sets differ from schema.py; refusing to load")
        klass = JointModel if meta.get("family") == JointModel.family else TransformerExtractor
        obj = klass.__new__(klass)
        TransformerExtractor.__init__(obj, meta["model_key"], meta["checkpoint"],
                                      classes=meta.get("classes"), device=device,
                                      threshold=meta.get("threshold"), **meta["cfg"])
        obj.train_info = meta.get("train_info", {})
        obj.fit_time_s = obj.train_info.get("train_time_s")
        obj.net, obj.tok = obj._load_weights(directory)
        obj.net.to(pick_device(device)).eval()
        return obj

    def release(self):
        torch = _torch()
        self.net = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()


class JointModel(TransformerExtractor):
    """Experiment 2: one model that classifies AND extracts in a single forward pass."""
    family = "joint"

    def __init__(self, model_key, checkpoint, classes, device="auto", threshold=None, **hp):
        if classes is None:
            raise ValueError("a joint model needs its class list")
        super().__init__(model_key, checkpoint, classes=classes, device=device,
                         threshold=threshold, **hp)


def build_extractor(model, **overrides):
    cfg = dict(S.EXTRACTOR_MODELS[model])
    cfg.update(overrides)
    return TransformerExtractor(model, cfg.pop("checkpoint"), **cfg)


def build_joint(model, classes, **overrides):
    cfg = dict(S.JOINT_MODELS[model])
    cfg.update(overrides)
    cfg.setdefault("threshold", S.TRANSACTION_THRESHOLD)
    return JointModel(model, cfg.pop("checkpoint"), classes, **cfg)
