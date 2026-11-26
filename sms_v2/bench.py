"""Two-stage SMS benchmark: one command line for every step.

    python bench.py prepare                       # labels + audit + splits + report
    python bench.py classify --models tfidf_lr,tfidf_svm,tfidf_nb --experiments binary,multiclass
    python bench.py classify --models marbert --experiments binary      # GPU advised
    python bench.py extract                       # standalone extraction (Stage 2 only)
    python bench.py e2e                           # end-to-end, every finished classifier
    python bench.py compare                       # tables + charts
    python bench.py status                        # what is done / failed / missing
    python bench.py predict --model-dir <dir> "SMS text"   # the live pipeline

All results land under config.settings.OUTPUT_ROOT (env SMS_V2_OUTPUT).
Nothing completed is redone or overwritten without --overwrite.
"""
import argparse
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from config import settings as S                      # noqa: E402


def _csv(s):
    return [x.strip() for x in s.split(",") if x.strip()]


def cmd_prepare(a):
    from collections import Counter
    from benchmark import data as D
    from benchmark import splits as SP
    from benchmark import store
    records = D.load()
    problems = D.validate(records)
    if problems:
        print("LABEL PROBLEMS:\n  " + "\n  ".join(problems[:30]))
        raise SystemExit(1)
    audit, lab = D.write_audit(records)
    print(f"{len(records)} records; labels validated; audit -> {audit}")
    print("binary    ", dict(Counter(r["label_binary"] for r in records)))
    print("multiclass", dict(Counter(r["label_multi"] for r in records)))
    report = {"n_records": len(records), "data_hash": D.data_hash(S.DATA_PATH),
              "binary": dict(Counter(r["label_binary"] for r in records)),
              "multiclass": dict(Counter(r["label_multi"] for r in records)),
              "multiclass_by_reason": dict(Counter(r["label_reason"] for r in records)),
              "splits": {}}
    for st in _csv(a.splits):
        path = SP.split_path(st)
        if os.path.exists(path) and not a.overwrite_splits:
            records_sides, payload = SP.load(records, st)
            print(f"\nsplit {st}: loaded existing {path}")
        else:
            payload = SP.create(records, st, overwrite=a.overwrite_splits)
            print(f"\nsplit {st}: created {path}")
        report["splits"][st] = {"grouping": payload["grouping"], "summary": payload["summary"]}
        for side, d in payload["summary"].items():
            print(f"  {side:5s} n={d['n']:5d}  {json.dumps(d['multiclass'], sort_keys=True)}")
    store.write_json(os.path.join(S.PROCESSED_DIR, "dataset_report.json"), report)
    print(f"\nreport -> {os.path.join(S.PROCESSED_DIR, 'dataset_report.json')}")


def cmd_classify(a):
    from benchmark import run_classify
    from benchmark import store
    failures = []
    for split in _csv(a.splits):
        for exp in _csv(a.experiments):
            for model in _csv(a.models):
                try:
                    run_classify.run(split, exp, model, overwrite=a.overwrite,
                                     keep_checkpoints=a.keep_checkpoints, device=a.device,
                                     overrides=json.loads(a.override) if a.override else None)
                except Exception as e:            # recorded in the log by store.Run
                    failures.append((split, exp, model, f"{type(e).__name__}: {e}"))
                    print(f"!! FAILED {split}/{exp}/{model}: {type(e).__name__}: {e}")
                    if a.stop_on_error:
                        raise
    if failures:
        print(f"\n{len(failures)} run(s) failed (see {store.root()}/experiment_log.jsonl):")
        for f in failures:
            print("  ", *f)
        raise SystemExit(1)


def cmd_extract(a):
    from benchmark import run_extract
    for split in _csv(a.splits):
        run_extract.run(split, overwrite=a.overwrite)


def cmd_e2e(a):
    from benchmark import run_e2e
    for split in _csv(a.splits):
        run_e2e.run(split, models=_csv(a.models) if a.models else None,
                    experiments=_csv(a.experiments), overwrite=a.overwrite)


def cmd_compare(a):
    from evaluation import compare_models
    for split in _csv(a.splits):
        compare_models.run(split, make_charts=not a.no_charts)


def cmd_status(a):
    from benchmark import status
    status.print_status(_csv(a.splits))


def cmd_predict(a):
    from sms_pipeline import SmsPipeline
    pipe = SmsPipeline.from_dirs(a.model_dir, a.extractor_dir, device=a.device)
    texts = a.sms or [line.rstrip("\n") for line in sys.stdin if line.strip()]
    for out in pipe.process_many(texts):
        print(json.dumps(out, ensure_ascii=False, indent=None if a.compact else 2))


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("prepare", help="labels, audit, splits")
    p.add_argument("--splits", default=",".join(S.SPLIT_STRATEGIES))
    p.add_argument("--overwrite-splits", action="store_true")
    p.set_defaults(fn=cmd_prepare)

    p = sub.add_parser("classify", help="train + evaluate Stage-1 classifiers")
    p.add_argument("--models", default="tfidf_lr,tfidf_svm,tfidf_nb,v1_gate")
    p.add_argument("--experiments", default=",".join(S.EXPERIMENTS))
    p.add_argument("--splits", default=S.PRIMARY_SPLIT)
    p.add_argument("--overwrite", action="store_true", help="redo completed runs")
    p.add_argument("--keep-checkpoints", action="store_true",
                   help="keep transformer epoch checkpoints after a run completes")
    p.add_argument("--device", default="auto")
    p.add_argument("--override", default=None,
                   help='JSON of hyperparameter overrides, e.g. \'{"epochs": 1, "batch_size": 8}\'')
    p.add_argument("--stop-on-error", action="store_true")
    p.set_defaults(fn=cmd_classify)

    p = sub.add_parser("extract", help="standalone Stage-2 evaluation")
    p.add_argument("--splits", default=S.PRIMARY_SPLIT)
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(fn=cmd_extract)

    p = sub.add_parser("e2e", help="end-to-end pipeline evaluation")
    p.add_argument("--splits", default=S.PRIMARY_SPLIT)
    p.add_argument("--models", default=None, help="default: every completed classifier")
    p.add_argument("--experiments", default=",".join(S.EXPERIMENTS))
    p.add_argument("--overwrite", action="store_true")
    p.set_defaults(fn=cmd_e2e)

    p = sub.add_parser("compare", help="comparison tables and charts")
    p.add_argument("--splits", default=S.PRIMARY_SPLIT)
    p.add_argument("--no-charts", action="store_true")
    p.set_defaults(fn=cmd_compare)

    p = sub.add_parser("status", help="done / failed / missing runs")
    p.add_argument("--splits", default=S.PRIMARY_SPLIT)
    p.set_defaults(fn=cmd_status)

    p = sub.add_parser("predict", help="run the two-stage pipeline on messages")
    p.add_argument("sms", nargs="*")
    p.add_argument("--model-dir", required=True, help="a classifier's final/ directory")
    p.add_argument("--extractor-dir", required=True, help="a fitted extractor directory")
    p.add_argument("--device", default="auto")
    p.add_argument("--compact", action="store_true")
    p.set_defaults(fn=cmd_predict)

    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
