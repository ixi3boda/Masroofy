"""Experiment 1: classifier x extractor combinations, end to end, on the test set.

    run("template", "binary", classifier="arabert", extractor="marbert")

Inputs (read only, never modified):
  * the classifier's FINISHED run: results/<split>/<experiment>/<clf>/ (predictions.csv
    = its routing decision per test message, metrics.json = its classification
    numbers and timing) and models/<split>/<experiment>/<clf>/final/;
  * the extractor's FINISHED run: results/<split>/extractors/<ext>/ (its output for
    every test message) and models/<split>/extractor/<ext>/final/.

Scoring is exactly the existing end-to-end evaluation (evaluation/end_to_end_metrics.py:
every gold transaction counts, misses scored wrong, false records counted), applied to
"routed by this classifier" x "extracted by this extractor".

Live check (S.COMBO_LATENCY_SAMPLE messages): the real SmsPipeline is loaded from the
two directories and run ONE SMS AT A TIME, which measures the actual per-SMS latency of
each stage and verifies that the live SMS -> JSON output equals the cached composition.

Writes results/<split>/combos/<experiment>/<clf>__<ext>/:
  config.json, metrics.json, predictions.jsonl (final JSON per test SMS),
  outcomes.csv, confusion_matrix.csv, DONE.json
"""
import csv
import json
import os
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
from evaluation import end_to_end_metrics as E2E      # noqa: E402

RECORD_FIELDS = ["is_transaction", "amount", "currency", "direction", "type", "channel",
                 "counterparty", "date", "datetime", "account_last4", "fee", "balance_after"]


def _read_predictions(path):
    with open(path, encoding="utf-8-sig") as f:
        return {int(r["id"]): r for r in csv.DictReader(f)}


def _final_json(pred_row, output, require_amount):
    """The pipeline's per-message answer, rebuilt from the cached stages."""
    routed = pred_row["routed_to_extraction"] == "1"
    rec, reason = None, None
    if not routed:
        reason = f"stage 1: {pred_row['pred']}"
    elif not output["extraction_ok"] and require_amount:
        reason = "stage 2: " + (output.get("extraction_note") or "no amount found")
    else:
        rec = output
    return {"label": pred_row["pred"], "routed": routed, "is_transaction": rec is not None,
            "record": rec, "reason": reason}


def _same(a, b):
    """Live vs cached record, compared on the graded fields (floats within 1e-6)."""
    if (a is None) != (b is None):
        return False
    if a is None:
        return True
    for k in RECORD_FIELDS[1:]:
        x, y = a.get(k), b.get(k)
        if isinstance(x, float) and isinstance(y, float):
            if abs(x - y) > 1e-6:
                return False
        elif x != y:
            return False
    return True


def live_check(split, experiment, classifier, extractor, test_records, cached, n, device, log):
    """Run the real pipeline one SMS at a time on the first n test messages."""
    if n <= 0:
        return None
    from sms_pipeline import SmsPipeline
    torch = run_extract_tf._cuda()

    def sync():
        if torch is not None:
            torch.cuda.synchronize()

    t0 = time.perf_counter()
    pipe = SmsPipeline.from_combo(split, experiment, classifier, extractor, device=device)
    load_s = time.perf_counter() - t0
    sample = test_records[:n]
    pipe.process(sample[0]["sms"])                                  # warm-up
    clf_ms, ext_ms, total_ms, agree, label_agree = [], [], [], 0, 0
    for r in sample:
        sync()
        t1 = time.perf_counter()
        labels, _ = pipe.clf.predict_with_scores([r["sms"]])
        sync()
        t2 = time.perf_counter()
        if labels[0] == L.TRANSACTION:
            pipe.extractor.extract_many([r["sms"]])
            sync()
            ext_ms.append(1000 * (time.perf_counter() - t2))
        clf_ms.append(1000 * (t2 - t1))
        t3 = time.perf_counter()
        out = pipe.process(r["sms"])                                 # the one-call SMS -> JSON
        sync()
        total_ms.append(1000 * (time.perf_counter() - t3))
        c = cached[r["id"]]
        label_agree += out["stage1"]["label"] == c["label"]
        agree += out["stage1"]["label"] == c["label"] and _same(out["record"], c["record"])
    for m in (pipe.clf, pipe.extractor):
        getattr(m, "release", lambda: None)()

    def stats(v):
        return {"median": float(np.median(v)), "p95": float(np.percentile(v, 95)),
                "n": len(v)} if v else None

    res = {"n": len(sample), "device": device, "load_time_s": load_s,
           "classification_ms": stats(clf_ms), "extraction_ms_routed": stats(ext_ms),
           "pipeline_ms": stats(total_ms),
           "label_agreement_with_cached": label_agree / len(sample),
           "output_agreement_with_cached": agree / len(sample)}
    if agree < len(sample):
        log(f"    note: live pipeline matched the cached result on {agree}/{len(sample)} "
            "messages (fp16 on GPU can flip near-ties)")
    return res


def run(split, experiment, classifier, extractor, overwrite=False, live_latency=None,
        device="auto", log=print):
    live_latency = S.COMBO_LATENCY_SAMPLE if live_latency is None else live_latency
    crdir, cfinal = layout.require_classifier(split, experiment, classifier)
    erdir, efinal = layout.require_extractor(split, extractor)
    for d, what in ((cfinal, "classifier"), (efinal, "extractor")):
        if not os.path.isdir(d):
            raise layout.MissingCheckpoint(f"the {what} run is marked done but its weights "
                                           f"are missing: {d}")
    cm = store.read_json(os.path.join(crdir, "metrics.json"))
    em = store.read_json(os.path.join(erdir, "metrics.json"))
    if cm.get("family") != "transformer":
        log(f"  note: {classifier} is a {cm.get('family')} classifier")
    rdir = layout.combo_result_dir(split, experiment, classifier, extractor)
    sources = {"classifier_finished": cm["finished"], "extractor_finished": em["finished"],
               "live_latency": live_latency}
    if store.is_done(rdir) and not overwrite:
        cached = store.read_json(os.path.join(rdir, "metrics.json"))
        if cached.get("sources") == sources:
            log(f"skip combo {split}/{experiment}/{layout.combo_name(classifier, extractor)}: "
                "already complete")
            return cached
        log("  inputs changed since the last run, recomputing")
    store.clear(rdir)

    records = D.load()
    sides, split_meta = SP.load(records, split)
    te = sides["test"]
    preds = _read_predictions(os.path.join(crdir, "predictions.csv"))
    outputs = run_extract_tf.load_predictions(split, extractor)
    missing = [r["id"] for r in te if r["id"] not in preds or r["id"] not in outputs]
    if missing:
        raise ValueError(f"{len(missing)} test ids lack predictions — the split changed after "
                         "one of the two runs; rerun it with --overwrite")
    if cm.get("data_hash") != em.get("data_hash"):
        raise ValueError("classifier and extractor were run on different data (hash mismatch)")

    name = layout.combo_name(classifier, extractor)
    with store.Run("combo", split=split, experiment=experiment, model=name):
        log(f"=== combo {split} / {experiment} / {classifier} classifier -> {extractor} extractor")
        routed = {i: p["routed_to_extraction"] == "1" for i, p in preds.items()}
        res, outcomes = E2E.compute(te, routed, outputs, require_amount=S.REQUIRE_AMOUNT)
        final = {r["id"]: _final_json(preds[r["id"]], outputs[r["id"]]["output"],
                                      S.REQUIRE_AMOUNT) for r in te}
        live = live_check(split, experiment, classifier, extractor, te, final, live_latency,
                          device, log)

        share = sum(routed[r["id"]] for r in te) / len(te)
        clf_ms = cm["timing"]["batch_ms_per_sms"]
        ext_ms = em["timing"]["ms_per_sms"]
        test = cm["test"]
        metrics = {
            "split": split, "experiment": experiment, "combination": name,
            "classifier": classifier, "extractor": extractor,
            "classifier_checkpoint": store.read_json(
                os.path.join(cfinal, "classifier.json")).get("checkpoint"),
            "extractor_checkpoint": em.get("checkpoint"),
            "classification": {
                "classes": cm["classes"], "accuracy": test["accuracy"],
                "macro_precision": test["macro_precision"], "macro_recall": test["macro_recall"],
                "macro_f1": test["macro_f1"], "weighted_f1": test.get("weighted_f1"),
                "per_class": test["per_class"], "confusion_matrix": test["confusion_matrix"],
                "routing": test["routing"]},
            **res,
            "timing": {"classifier_ms_per_sms_batch": clf_ms,
                       "classifier_ms_per_sms_single": cm["timing"].get("single_ms_per_sms_median"),
                       "extractor_ms_per_sms_batch": ext_ms,
                       "extractor_ms_per_sms_single": em["timing"].get("single_ms_per_sms_median"),
                       "share_routed": share,
                       "pipeline_ms_per_sms": clf_ms + share * ext_ms,
                       "classifier_device": (cm.get("train") or {}).get("device"),
                       "extractor_device": (em.get("train") or {}).get("device"),
                       "live": live},
            "require_amount": S.REQUIRE_AMOUNT, "sources": sources,
            "split_seed": split_meta["seed"], "data_hash": split_meta["data_hash"],
            "environment": store.environment(), "finished": store.now()}
        store.write_json(os.path.join(rdir, "config.json"),
                         {"split": split, "experiment": experiment, "classifier": classifier,
                          "extractor": extractor, "classifier_result_dir": crdir,
                          "classifier_model_dir": cfinal, "extractor_result_dir": erdir,
                          "extractor_model_dir": efinal, "require_amount": S.REQUIRE_AMOUNT,
                          "live_latency_sample": live_latency})
        store.write_json(os.path.join(rdir, "metrics.json"), metrics)
        tmp = os.path.join(rdir, "predictions.jsonl.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            for r in te:
                f.write(json.dumps({"id": r["id"], "gold": r[D.label_column(experiment)],
                                    **final[r["id"]]}, ensure_ascii=False) + "\n")
        os.replace(tmp, os.path.join(rdir, "predictions.jsonl"))
        store.write_csv(os.path.join(rdir, "outcomes.csv"),
                        ["id", "gold", "pred", "routed", "outcome", "reason", "exact"],
                        [[o["id"], preds[o["id"]]["gold"], preds[o["id"]]["pred"],
                          int(routed[o["id"]]), o["outcome"], o["reason"], int(o["exact"])]
                         for o in outcomes])
        cmx = test["confusion_matrix"]
        store.write_csv(os.path.join(rdir, "confusion_matrix.csv"), ["gold \\ pred"] + cmx["labels"],
                        [[c] + row for c, row in zip(cmx["labels"], cmx["matrix"])])
        store.mark_done(rdir)
        lat = f"  live {live['pipeline_ms']['median']:.1f} ms/SMS" if live else ""
        log(f"    macro-F1 {test['macro_f1']:.3f}  exact-record F1 {res['e2e_full_exact_f1']:.3f}  "
            f"missed {res['missed_transactions']}  false records {res['false_records']}  "
            f"{metrics['timing']['pipeline_ms_per_sms']:.2f} ms/SMS (batched){lat}")
    return metrics
