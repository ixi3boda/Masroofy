"""End-to-end evaluation: every finished classifier x the extractor, on the test set.

For a classifier, "routed" comes from its saved test predictions
(results/<split>/<experiment>/<model>/predictions.csv); the extractor's output
per message from results/<split>/extraction/predictions.jsonl. Combining the two
is exactly what SmsPipeline does live (classify -> extract only if routed), but
without reloading any transformer; tests/test_pipeline.py checks the two agree.

Also written: an "oracle" row (a perfect Stage 1), which is the ceiling the
classifiers are chasing, and equals standalone extraction plus perfect rejects.

Processing time per SMS = classifier batch ms/SMS + (share routed) x extractor
ms/SMS — the cost of the pipeline as actually run.
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from benchmark import data as D                       # noqa: E402
from benchmark import run_extract                     # noqa: E402
from benchmark import splits as SP                    # noqa: E402
from benchmark import store                           # noqa: E402
from classification import registry                   # noqa: E402
from config import settings as S                      # noqa: E402
from evaluation import end_to_end_metrics as E2E      # noqa: E402


def _routed(path):
    with open(path, encoding="utf-8-sig") as f:
        return {int(r["id"]): r["routed_to_extraction"] == "1" for r in csv.DictReader(f)}


def run(split, models=None, experiments=None, overwrite=False, log=print):
    records = D.load()
    sides, meta = SP.load(records, split)
    te = sides["test"]
    outputs = run_extract.load_predictions(split)
    ex_metrics = store.read_json(os.path.join(store.stage_dir(split, "extraction"), "metrics.json"))
    ex_ms = ex_metrics["timing"]["ms_per_sms"]
    base = store.stage_dir(split, "end_to_end")

    jobs = [("oracle", "oracle", {r["id"]: bool(r["expected"]["is_transaction"]) for r in te},
             0.0, None)]
    for exp in experiments or S.EXPERIMENTS:
        for model in models or registry.ALL:
            rdir = store.result_dir(split, exp, model)
            if not store.is_done(rdir):
                continue
            m = store.read_json(os.path.join(rdir, "metrics.json"))
            jobs.append((exp, model, _routed(os.path.join(rdir, "predictions.csv")),
                         m["timing"]["batch_ms_per_sms"], m["finished"]))

    results = []
    for exp, model, routed, clf_ms, clf_finished in jobs:
        out_dir = os.path.join(base, exp, model)
        # a cached result is reused only if it was built from the SAME classifier
        # and extraction runs; re-running either invalidates it automatically
        sources = {"classifier_finished": clf_finished,
                   "extraction_finished": ex_metrics["finished"]}
        if store.is_done(out_dir) and not overwrite:
            cached = store.read_json(os.path.join(out_dir, "metrics.json"))
            if cached.get("sources") == sources:
                results.append(cached)
                continue
            log(f"  e2e {exp}/{model}: inputs changed since last run, recomputing")
        store.clear(out_dir)
        missing = [r["id"] for r in te if r["id"] not in routed or r["id"] not in outputs]
        if missing:
            raise ValueError(f"{exp}/{model}: {len(missing)} test ids lack predictions — the "
                             "split changed after this classifier ran; rerun it with --overwrite")
        with store.Run("e2e", split=split, experiment=exp, model=model):
            res, outcomes = E2E.compute(te, routed, outputs, require_amount=S.REQUIRE_AMOUNT)
            share = sum(routed[r["id"]] for r in te) / len(te)
            res.update(split=split, experiment=exp, model=model,
                       extractor=ex_metrics["extractor"], require_amount=S.REQUIRE_AMOUNT,
                       timing={"classifier_ms_per_sms": clf_ms, "extractor_ms_per_sms": ex_ms,
                               "share_routed": share,
                               "pipeline_ms_per_sms": clf_ms + share * ex_ms},
                       sources=sources, finished=store.now())
            store.write_json(os.path.join(out_dir, "metrics.json"), res)
            store.write_csv(os.path.join(out_dir, "outcomes.csv"),
                            ["id", "outcome", "reason", "exact"],
                            [[o["id"], o["outcome"], o["reason"], int(o["exact"])]
                             for o in outcomes])
            store.mark_done(out_dir)
        results.append(res)
        log(f"  e2e {exp:10s} {model:12s} exact-record F1 {res['e2e_full_exact_f1']:.3f}  "
            f"missed {res['missed_transactions']:3d}  false records {res['false_records']:3d}  "
            f"{res['timing']['pipeline_ms_per_sms']:.2f} ms/SMS")
    return results
