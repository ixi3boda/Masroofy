"""Experiment 1, Stage 2: train + evaluate ONE transformer extractor on ONE split.

    run("template", "arabert")

Same discipline as run_classify / run_extract:
  1. train on the GOLD TRANSACTIONS of `train`; early stopping on gold val transactions;
  2. save final/;
  3. run it on EVERY test message ONCE and store the output per id
     (predictions.jsonl) — the combinations (run_combos.py) reuse these, because an
     extractor's output for a message does not depend on which classifier routed it;
  4. score standalone extraction on the gold test transactions (a perfect Stage 1);
  5. DONE.json last.

Writes results/<split>/extractors/<model>/ and models/<split>/extractor/<model>/final/.
The v1 extractor (models/<split>/extractor/v1_sklearn, results/<split>/extraction/) is
never touched.
"""
import json
import os
import shutil
import sys
import time

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import data as D                       # noqa: E402
from benchmark import layout                          # noqa: E402
from benchmark import splits as SP                    # noqa: E402
from benchmark import store                           # noqa: E402
from config import settings as S                      # noqa: E402
from evaluation import extraction_metrics as EM       # noqa: E402
from extraction.base import to_v1                     # noqa: E402

LATENCY_SAMPLE = 50


def _cuda():
    try:
        import torch
        return torch if torch.cuda.is_available() else None
    except ImportError:
        return None


def time_extraction(ex, texts):
    """-> (outputs, timing): batched throughput and one-SMS-at-a-time latency."""
    import numpy as np
    ex.extract_many(texts[:8])                                     # warm-up
    torch = _cuda()
    if torch is not None:
        torch.cuda.synchronize()
    t0 = time.perf_counter()
    outs = ex.extract_many(texts)
    if torch is not None:
        torch.cuda.synchronize()
    batch = time.perf_counter() - t0
    singles = []
    for t in texts[:LATENCY_SAMPLE]:
        t1 = time.perf_counter()
        ex.extract_many([t])
        if torch is not None:
            torch.cuda.synchronize()
        singles.append(time.perf_counter() - t1)
    return outs, {"n": len(texts), "batch_total_s": batch,
                  "ms_per_sms": 1000 * batch / max(len(texts), 1),
                  "single_ms_per_sms_median": 1000 * float(np.median(singles)) if singles else None,
                  "single_ms_per_sms_p95": 1000 * float(np.percentile(singles, 95)) if singles else None}


def standalone_metrics(test_records, outs):
    gold_tx = [(r, o) for r, o in zip(test_records, outs) if r["expected"]["is_transaction"]]
    pairs = [(r["expected"], to_v1(o) if o["extraction_ok"] else None) for r, o in gold_tx]
    fs = EM.field_scores(pairs)
    by_sender = {}
    for sender in sorted({r["sender"] for r, _ in gold_tx}):
        sub = [(r["expected"], to_v1(o) if o["extraction_ok"] else None)
               for r, o in gold_tx if r["sender"] == sender]
        by_sender[sender] = EM.headline(EM.field_scores(sub)) | {"n": len(sub)}
    return {"n_test_gold_transactions": len(gold_tx),
            "no_record_on_gold_transactions": sum(1 for _, o in gold_tx if not o["extraction_ok"]),
            "fields": fs, "headline": EM.headline(fs), "by_sender": by_sender}


def write_outputs(path, test_records, outs):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        for r, o in zip(test_records, outs):
            f.write(json.dumps({"id": r["id"], "output": o}, ensure_ascii=False) + "\n")
    os.replace(tmp, path)


def load_predictions(split, model):
    path = os.path.join(layout.extractor_result_dir(split, model), "predictions.jsonl")
    if not os.path.exists(path):
        raise layout.MissingCheckpoint(f"no {model} extraction outputs for {split}; run  "
                                       f"python bench.py extract-tf --models {model} --splits {split}")
    with open(path, encoding="utf-8") as f:
        return {r["id"]: r for r in map(json.loads, f)}


def run(split, model, overwrite=False, keep_checkpoints=False, device="auto", overrides=None,
        log=print):
    from extraction.transformer_extractor import build_extractor
    if model not in S.EXTRACTOR_MODELS:
        raise KeyError(f"unknown extractor {model!r}; known: {', '.join(S.EXTRACTOR_MODELS)}")
    rdir = layout.extractor_result_dir(split, model)
    mdir = layout.extractor_model_dir(split, model)
    cdir = layout.extractor_checkpoint_dir(split, model)
    backup = layout.extractor_backup(split, model, log=log)

    def wipe():
        store.clear(mdir)
        store.clear(cdir)
        if backup is not None:
            backup.release()

    if store.is_done(rdir):
        if not overwrite:
            log(f"skip extractor {split}/{model}: already complete ({rdir}). "
                "Pass --overwrite to redo it.")
            return store.read_json(os.path.join(rdir, "metrics.json"))
        store.clear(rdir)
        wipe()
    elif overwrite:
        wipe()

    records = D.load()
    sides, split_meta = SP.load(records, split)
    tr, va, te = sides["train"], sides["val"], sides["test"]
    overrides = dict(overrides or {})
    overrides.setdefault("device", device)
    ex = build_extractor(model, **overrides)

    with store.Run("extract_tf", split=split, extractor=model) as run_:
        n_tr = sum(r["expected"]["is_transaction"] for r in tr)
        n_va = sum(r["expected"]["is_transaction"] for r in va)
        log(f"=== extractor {split} / {model}: {n_tr} train / {n_va} val gold transactions, "
            f"{len(te)} test messages")
        info = ex.train(tr, va, work_dir=cdir, log=log, backup=backup)
        final = os.path.join(mdir, "final")
        ex.save(final)

        # ---- the only time this run touches the test set
        test_texts = [r["sms"] for r in te]
        outs, timing = time_extraction(ex, test_texts)
        write_outputs(os.path.join(rdir, "predictions.jsonl"), te, outs)
        sm = standalone_metrics(te, outs)
        metrics = {"split": split, "extractor": model, "family": ex.family,
                   "checkpoint": ex.checkpoint, "architecture": "marbert.py extractor: "
                   "encoder + BIO token head (17) + type head (7) + channel head (7)",
                   "n_train_transactions": n_tr, "n_val_transactions": n_va,
                   "n_test_messages": len(te), **sm, "train": info,
                   "timing": {"fit_time_s": info["train_time_s"], **timing},
                   "model_size_mb": store.dir_size(final) / 2 ** 20,
                   "n_parameters": ex.n_parameters(),
                   "reference_field": "extracted by rule, not evaluated: the corpus has "
                                      "no gold reference ids",
                   "split_seed": split_meta["seed"], "data_hash": split_meta["data_hash"],
                   "environment": store.environment(), "finished": store.now()}
        store.write_json(os.path.join(rdir, "config.json"),
                         {"split": split, "extractor": model, "checkpoint": ex.checkpoint,
                          "cfg": ex.cfg, "input_preprocessing": ex.preprocessing,
                          "selection": ex.selection_rule(), "model_dir": final})
        store.write_json(os.path.join(rdir, "metrics.json"), metrics)
        store.mark_done(rdir, model_dir=final)
        h = metrics["headline"]
        run_.info.update(full_record_exact=h["full_record_exact"])
        log(f"    {sm['n_test_gold_transactions']} gold transactions: amount {h['amount_acc']:.3f}  "
            f"currency {h['currency_acc']:.3f}  counterparty F1 {h['counterparty_f1']:.3f}  "
            f"date {h['date_acc']:.3f}  direction {h['direction_acc']:.3f}  "
            f"full {h['full_record_exact']:.3f} | {timing['ms_per_sms']:.2f} ms/SMS")

    if not keep_checkpoints:
        shutil.rmtree(os.path.join(cdir, "checkpoints"), ignore_errors=True)
        if backup is not None:
            backup.release()
    ex.release()
    return metrics
