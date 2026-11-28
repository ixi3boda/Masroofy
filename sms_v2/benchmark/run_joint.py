"""Experiment 2: ONE joint model (classifier + extractor in one network), trained and
evaluated as one workflow.

    run("template", "multiclass", "arabert")

`experiment` picks the class head's label set — the EXISTING gold labels, unchanged:
  binary      transaction / non_transaction      (label_binary)
  multiclass  the 6 classes of config/labels.py  (label_multi)

Order of events (same as run_classify, which keeps the test set honest):
  1. train on `train` (all messages: class loss on every message, extraction losses on
     gold transactions); early stopping on `val`;
  2. save final/;
  3. score `val` (reported);
  4. ONE pass over `test`: class + record per message, timed; classification metrics,
     standalone extraction (gold transactions), end to end (its own routing). DONE last.

Writes results/<split>/joint/<experiment>/<model>/:
  config.json, metrics.json, predictions.csv (class per message, same columns as the
  classifiers'), extraction_predictions.jsonl, predictions.jsonl (final JSON per SMS),
  outcomes.csv, confusion_matrix.csv, DONE.json
and models/<split>/joint/<experiment>/<model>/final/. Nothing existing is touched.
"""
import json
import os
import shutil
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import data as D                       # noqa: E402
from benchmark import layout                          # noqa: E402
from benchmark import run_extract_tf                  # noqa: E402
from benchmark import splits as SP                    # noqa: E402
from benchmark import store                           # noqa: E402
from config import labels as L                        # noqa: E402
from config import settings as S                      # noqa: E402
from evaluation import classification_metrics as CM   # noqa: E402
from evaluation import end_to_end_metrics as E2E      # noqa: E402

LATENCY_SAMPLE = 50


def time_joint(model, texts):
    """-> (labels, probs, outputs, timing). One forward pass gives everything."""
    model.infer(texts[:8])
    torch = run_extract_tf._cuda()
    if torch is not None:
        torch.cuda.synchronize()
        torch.cuda.reset_peak_memory_stats()
    t0 = time.perf_counter()
    labels, probs, outs = model.infer(texts)
    if torch is not None:
        torch.cuda.synchronize()
    batch = time.perf_counter() - t0
    singles = []
    for t in texts[:LATENCY_SAMPLE]:
        t1 = time.perf_counter()
        model.infer([t])
        if torch is not None:
            torch.cuda.synchronize()
        singles.append(time.perf_counter() - t1)
    return labels, probs, outs, {
        "n": len(texts), "batch_total_s": batch,
        "batch_ms_per_sms": 1000 * batch / max(len(texts), 1),
        "single_ms_per_sms_median": 1000 * float(np.median(singles)) if singles else None,
        "single_ms_per_sms_p95": 1000 * float(np.percentile(singles, 95)) if singles else None,
        "peak_gpu_mem_infer_mb": (torch.cuda.max_memory_allocated() / 2 ** 20
                                  if torch is not None else None)}


def run(split, experiment, model, overwrite=False, keep_checkpoints=False, device="auto",
        overrides=None, log=print):
    from extraction.transformer_extractor import build_joint
    if model not in S.JOINT_MODELS:
        raise KeyError(f"unknown joint model {model!r}; known: {', '.join(S.JOINT_MODELS)}")
    if S.PREPROCESSING != "digits":
        raise ValueError("the joint model shares one input between classification and "
                         "extraction, which needs the length-preserving 'digits' preprocessing; "
                         f"config says {S.PREPROCESSING!r}, so it would not be comparable")
    rdir = layout.joint_result_dir(split, experiment, model)
    mdir = layout.joint_model_dir(split, experiment, model)
    cdir = layout.joint_checkpoint_dir(split, experiment, model)
    backup = layout.joint_backup(split, experiment, model, log=log)

    def wipe():
        store.clear(mdir)
        store.clear(cdir)
        if backup is not None:
            backup.release()

    if store.is_done(rdir):
        if not overwrite:
            log(f"skip joint {split}/{experiment}/{model}: already complete ({rdir}). "
                "Pass --overwrite to redo it.")
            return store.read_json(os.path.join(rdir, "metrics.json"))
        store.clear(rdir)
        wipe()
    elif overwrite:
        wipe()

    records = D.load()
    sides, split_meta = SP.load(records, split)
    col, classes = D.label_column(experiment), D.class_list(experiment)
    tr, va, te = sides["train"], sides["val"], sides["test"]
    overrides = dict(overrides or {})
    overrides.setdefault("device", device)
    jm = build_joint(model, classes, **overrides)

    with store.Run("joint", split=split, experiment=experiment, model=model) as run_:
        log(f"=== joint {split} / {experiment} / {model}: {len(tr)} train, {len(va)} val, "
            f"{len(te)} test (one model: class head + extraction heads)")
        info = jm.train(tr, va, work_dir=cdir, label_col=col, log=log, backup=backup)
        final = os.path.join(mdir, "final")
        jm.save(final)

        val_labels, _, _ = jm.infer([r["sms"] for r in va])
        val_res = CM.compute([r[col] for r in va], val_labels, classes,
                             gold_multi=[r["label_multi"] for r in va])

        # ---- the only time this run touches the test set
        labels, probs, outs, timing = time_joint(jm, [r["sms"] for r in te])
        test_res = CM.compute([r[col] for r in te], labels, classes,
                              gold_multi=[r["label_multi"] for r in te])
        tx = classes.index(L.TRANSACTION)
        store.write_csv(os.path.join(rdir, "predictions.csv"),
                        ["id", "sender", "category", "gold", "gold_multiclass", "pred",
                         "routed_to_extraction", "transaction_score"],
                        [[r["id"], r["sender"], r["category"], r[col], r["label_multi"], p,
                          int(p == L.TRANSACTION), float(s[tx])]
                         for r, p, s in zip(te, labels, probs)])
        cmx = test_res["confusion_matrix"]
        store.write_csv(os.path.join(rdir, "confusion_matrix.csv"), ["gold \\ pred"] + classes,
                        [[c] + row for c, row in zip(classes, cmx["matrix"])])
        run_extract_tf.write_outputs(os.path.join(rdir, "extraction_predictions.jsonl"), te, outs)

        standalone = run_extract_tf.standalone_metrics(te, outs)
        routed = {r["id"]: p == L.TRANSACTION for r, p in zip(te, labels)}
        out_by_id = {r["id"]: {"id": r["id"], "output": o} for r, o in zip(te, outs)}
        e2e, outcomes = E2E.compute(te, routed, out_by_id, require_amount=S.REQUIRE_AMOUNT)

        tmp = os.path.join(rdir, "predictions.jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for r, p, o in zip(te, labels, outs):
                rec, reason = None, None
                if p != L.TRANSACTION:
                    reason = f"stage 1: {p}"
                elif not o["extraction_ok"] and S.REQUIRE_AMOUNT:
                    reason = "stage 2: " + (o.get("extraction_note") or "no amount found")
                else:
                    rec = o
                f.write(json.dumps({"id": r["id"], "gold": r[col], "label": p,
                                    "routed": p == L.TRANSACTION, "is_transaction": rec is not None,
                                    "record": rec, "reason": reason}, ensure_ascii=False) + "\n")
        os.replace(tmp, os.path.join(rdir, "predictions.jsonl"))
        store.write_csv(os.path.join(rdir, "outcomes.csv"),
                        ["id", "outcome", "reason", "exact"],
                        [[o["id"], o["outcome"], o["reason"], int(o["exact"])] for o in outcomes])

        metrics = {"split": split, "experiment": experiment, "model": f"joint_{model}",
                   "workflow": "joint", "family": jm.family, "checkpoint": jm.checkpoint,
                   "classes": classes, "score_type": "probability", "threshold": jm.threshold,
                   "preprocessing": jm.preprocessing,
                   "n_train": len(tr), "n_val": len(va), "n_test": len(te),
                   "train": info, "val": val_res, "test": test_res,
                   "extraction_standalone": standalone,
                   "end_to_end": e2e,
                   "timing": {"train_time_s": info["train_time_s"], **timing,
                              "pipeline_ms_per_sms": timing["batch_ms_per_sms"],
                              "note": "one forward pass yields class and record; there is "
                                      "no separate extraction time"},
                   "model_size_mb": store.dir_size(final) / 2 ** 20,
                   "n_parameters": jm.n_parameters(),
                   "split_seed": split_meta["seed"], "data_hash": split_meta["data_hash"],
                   "environment": store.environment(), "finished": store.now()}
        store.write_json(os.path.join(rdir, "config.json"),
                         {"split": split, "experiment": experiment, "model": model,
                          "checkpoint": jm.checkpoint, "classes": classes, "label_column": col,
                          "cfg": jm.cfg, "selection": jm.selection_rule(),
                          "loss": "class-weighted CE (class head) + token CE + type CE + "
                                  "channel CE (extraction heads, gold transactions only)",
                          "model_dir": final})
        store.write_json(os.path.join(rdir, "metrics.json"), metrics)
        store.mark_done(rdir, model_dir=final)
        h = CM.headline(test_res)
        run_.info.update(test_macro_f1=h["macro_f1"], e2e_exact_f1=e2e["e2e_full_exact_f1"])
        def f4(v):
            return "n/a" if v is None else f"{v:.4f}"
        log(f"    test macro-F1 {f4(h['macro_f1'])}  tx recall {f4(h['transaction_recall'])}  "
            f"tx precision {f4(h['transaction_precision'])}  exact-record F1 "
            f"{e2e['e2e_full_exact_f1']:.3f}  missed {e2e['missed_transactions']}  "
            f"false records {e2e['false_records']}  | {timing['batch_ms_per_sms']:.2f} ms/SMS")

    if not keep_checkpoints:
        shutil.rmtree(os.path.join(cdir, "checkpoints"), ignore_errors=True)
        if backup is not None:
            backup.release()
    jm.release()
    return metrics
