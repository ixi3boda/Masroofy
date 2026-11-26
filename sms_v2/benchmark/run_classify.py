"""Train + evaluate ONE classifier on ONE split for ONE experiment.

    run(split="template", experiment="binary", model="tfidf_lr")

Order of events, which is what keeps the test set honest:
  1. train on `train`; any model selection (grid search, early stopping) uses
     `val` only;
  2. save the final model;
  3. score `val` (reported as the selection-set number);
  4. score `test` ONCE, write metrics + per-message predictions, write DONE.

The per-message test predictions (predictions.csv) are what the end-to-end
evaluation reads, so a transformer never has to be reloaded to evaluate the
pipeline.

A completed run (DONE.json present) is skipped unless overwrite=True. A
transformer run that was interrupted resumes from its last epoch checkpoint.
"""
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import data as D                       # noqa: E402
from benchmark import splits as SP                    # noqa: E402
from benchmark import store                           # noqa: E402
from classification import registry                   # noqa: E402
from config import labels as L                        # noqa: E402
from evaluation import classification_metrics as CM   # noqa: E402

LATENCY_SAMPLE = 50          # messages timed one at a time, for per-SMS latency


def _rss_mb():
    try:
        import psutil
        return psutil.Process().memory_info().rss / 2 ** 20
    except ImportError:
        return None


def _cuda():
    try:
        import torch
        return torch if torch.cuda.is_available() else None
    except ImportError:
        return None


def time_inference(clf, texts):
    """-> (labels, scores, timing dict). Batch throughput AND single-SMS latency."""
    clf.predict_with_scores(texts[:8])                 # warm-up (CUDA kernels, caches)
    torch = _cuda()
    if torch is not None:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    labels, scores = clf.predict_with_scores(texts)
    if torch is not None:
        torch.cuda.synchronize()
    batch_s = time.perf_counter() - t0
    singles = []
    for t in texts[:LATENCY_SAMPLE]:
        t1 = time.perf_counter()
        clf.predict_with_scores([t])
        if torch is not None:
            torch.cuda.synchronize()
        singles.append(time.perf_counter() - t1)
    timing = {"n": len(texts), "batch_total_s": batch_s,
              "batch_ms_per_sms": 1000 * batch_s / max(len(texts), 1),
              "single_ms_per_sms_median": 1000 * float(np.median(singles)) if singles else None,
              "single_ms_per_sms_p95": 1000 * float(np.percentile(singles, 95)) if singles else None,
              "peak_gpu_mem_infer_mb": (torch.cuda.max_memory_allocated() / 2 ** 20
                                        if torch is not None else None),
              "process_rss_mb": _rss_mb()}
    return labels, np.asarray(scores), timing


def _param_count(clf):
    m = getattr(clf, "model", None)
    if m is not None and hasattr(m, "parameters"):
        return int(sum(p.numel() for p in m.parameters()))
    return None


def run(split, experiment, model, overwrite=False, keep_checkpoints=False,
        device="auto", overrides=None, log=print):
    rdir = store.result_dir(split, experiment, model)
    mdir = store.model_dir(split, experiment, model)
    if model in registry.REFERENCE and experiment != "binary":
        log(f"skip {model}/{experiment}: reference model is binary only")
        return None
    is_tf = registry.family(model) == "transformer"
    cdir = store.checkpoint_dir(split, experiment, model) if is_tf else mdir
    backup = store.checkpoint_backup(split, experiment, model, log=log) if is_tf else None

    def wipe_training_state():
        store.clear(mdir)
        store.clear(cdir)
        if backup is not None:
            backup.release()

    if store.is_done(rdir):
        if not overwrite:
            log(f"skip {split}/{experiment}/{model}: already complete ({rdir}). "
                "Pass --overwrite to redo it.")
            return store.read_json(os.path.join(rdir, "metrics.json"))
        store.clear(rdir)
        wipe_training_state()
    elif overwrite:
        wipe_training_state()

    records = D.load()
    sides, split_meta = SP.load(records, split)
    col, classes = D.label_column(experiment), D.class_list(experiment)
    tr, va, te = sides["train"], sides["val"], sides["test"]

    overrides = dict(overrides or {})
    if is_tf:
        overrides.setdefault("device", device)
    clf = registry.build(model, classes, **overrides)
    extra = {"backup": backup} if is_tf else {}

    ident = dict(split=split, experiment=experiment, model=model)
    with store.Run("classify", **ident) as run_:
        log(f"=== {split} / {experiment} / {model}: {len(tr)} train, {len(va)} val, "
            f"{len(te)} test")
        info = clf.train([r["sms"] for r in tr], [r[col] for r in tr],
                         [r["sms"] for r in va], [r[col] for r in va],
                         work_dir=cdir, train_ids=[r["id"] for r in tr],
                         train_records=tr, log=log, **extra)
        final = os.path.join(mdir, "final")
        clf.save(final)

        val_pred = clf.predict([r["sms"] for r in va])
        val_res = CM.compute([r[col] for r in va], val_pred, classes,
                             gold_multi=[r["label_multi"] for r in va])

        # ---- final evaluation: the only time this run touches the test set
        test_texts = [r["sms"] for r in te]
        pred, scores, timing = time_inference(clf, test_texts)
        test_res = CM.compute([r[col] for r in te], pred, classes,
                              gold_multi=[r["label_multi"] for r in te])

        tx = classes.index(L.TRANSACTION)
        rows = [[r["id"], r["sender"], r["category"], r[col], r["label_multi"], p,
                 int(p == L.TRANSACTION), float(s[tx])]
                for r, p, s in zip(te, pred, scores)]
        store.write_csv(os.path.join(rdir, "predictions.csv"),
                        ["id", "sender", "category", "gold", "gold_multiclass", "pred",
                         "routed_to_extraction", "transaction_score"], rows)
        cm = test_res["confusion_matrix"]
        store.write_csv(os.path.join(rdir, "confusion_matrix.csv"), ["gold \\ pred"] + classes,
                        [[c] + row for c, row in zip(classes, cm["matrix"])])

        metrics = {"split": split, "experiment": experiment, "model": model,
                   "family": clf.family, "classes": classes,
                   "score_type": clf.score_type, "threshold": clf.threshold,
                   "preprocessing": clf.preprocessing,
                   "n_train": len(tr), "n_val": len(va), "n_test": len(te),
                   "split_seed": split_meta["seed"], "data_hash": split_meta["data_hash"],
                   "train": info, "val": val_res, "test": test_res,
                   "timing": {"train_time_s": info.get("train_time_s"), **timing},
                   "model_size_mb": store.dir_size(final) / 2 ** 20,
                   "n_parameters": _param_count(clf),
                   "environment": store.environment(), "finished": store.now()}
        store.write_json(os.path.join(rdir, "metrics.json"), metrics)
        store.mark_done(rdir, model_dir=final)
        h = CM.headline(test_res)
        run_.info.update(test_macro_f1=h["macro_f1"], test_tx_recall=h["transaction_recall"],
                         test_tx_precision=h["transaction_precision"])
        log(f"    test macro-F1 {h['macro_f1']:.4f}  acc {h['accuracy']:.4f}  "
            f"tx recall {h['transaction_recall']:.4f}  tx precision "
            f"{h['transaction_precision']:.4f}  | {timing['batch_ms_per_sms']:.2f} ms/SMS")

    if is_tf and not keep_checkpoints:
        # final/ (on OUTPUT_ROOT) holds the best weights; the epoch checkpoints and
        # their backup are only needed while training. The backup slots are marked
        # free, not deleted: the next run overwrites them in place.
        shutil.rmtree(os.path.join(cdir, "checkpoints"), ignore_errors=True)
        if backup is not None:
            backup.release()
    clf.release()
    return metrics
