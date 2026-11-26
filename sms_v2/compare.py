"""v1 (sklearn, sms_eval_final) vs v2 (MARBERT, here) on identical data.

    python compare.py --splits random                 # needs runs/random/ trained
    python compare.py --splits random --v1-only       # baseline table, no torch
    python compare.py --splits random,real_formats

Fairness rules, because an unfair comparison is worse than none:
  * both implementations train on the SAME train rows and are scored on the SAME
    test rows, from dataset.split();
  * both are graded by sms_eval_final/evaluate.py:score() — the identical function
    that produced eval_report.txt, so metric definitions cannot drift;
  * v1 is retrained per split here rather than reusing the committed .joblib, so it
    never sees the test rows in training;
  * per-field accuracy is computed only over messages BOTH agree are transactions,
    which is how v1's score() has always worked — read tx_f1 and non_tx_rejected
    alongside it, or a model that rejects everything hard looks precise.

Writes compare_results.json and compare_report.txt next to this file.
"""
import argparse
import json
import os
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
V1_DIR = os.path.normpath(os.path.join(HERE, "..", "sms_eval_final"))
sys.path.insert(0, V1_DIR)

import dataset                                     # noqa: E402
from schema import FIELDS                           # noqa: E402

HEADLINE = ["tx_precision", "tx_recall", "tx_f1", "non_tx_rejected", "full_record_exact"]
ALL_METRICS = HEADLINE + FIELDS


def v1_predictions(train, test):
    """Train v1 on `train`, predict `test`. -> list of (record, prediction)."""
    from sms_model import SmsTxnModel
    model = SmsTxnModel().fit(train)
    return [(r, model.predict(r["sms"])) for r in test]


def v2_predictions(run_dir, test, device="auto"):
    import pipeline
    pipe = pipeline.load(run_dir, device)
    preds = pipe.predict_many([r["sms"] for r in test])
    return list(zip(test, preds))


def fmt(v):
    return "    -" if v is None else f"{v:5.3f}"


def delta(a, b):
    if a is None or b is None:
        return "     "
    d = b - a
    sign = "+" if d >= 0 else "-"
    return f"{sign}{abs(d):4.3f}"


def table(name, r1, r2, stream, labels=("v1 sklearn", "v2 MARBERT")):
    w = stream.write
    w(f"\n{'=' * 72}\n")
    w(f"=== {name}   (n={r1['n']})\n")
    w(f"{'=' * 72}\n")
    w(f"{'metric':20s} {labels[0]:>11s} {labels[1]:>11s} {'delta':>9s}\n")
    w(f"{'-' * 72}\n")
    for k in HEADLINE:
        w(f"{k:20s} {fmt(r1.get(k)):>11s} {fmt(r2.get(k)) if r2 else '     -':>11s} "
          f"{delta(r1.get(k), r2.get(k)) if r2 else '':>9s}\n")
    w(f"{'-' * 72}\n")
    w(f"{'per-field accuracy':20s}\n")
    for k in FIELDS:
        w(f"  {k:18s} {fmt(r1.get(k)):>11s} {fmt(r2.get(k)) if r2 else '     -':>11s} "
          f"{delta(r1.get(k), r2.get(k)) if r2 else '':>9s}\n")


def sender_table(name, b1, b2, stream):
    w = stream.write
    w(f"\n  by sender ({name}): full_record_exact / tx_f1\n")
    w(f"  {'sender':14s} {'n':>5s}  {'v1 full':>8s} {'v2 full':>8s} {'d':>7s}   "
      f"{'v1 f1':>6s} {'v2 f1':>6s} {'d':>7s}\n")
    for sender in sorted(b1):
        a, b = b1[sender], (b2 or {}).get(sender)
        w(f"  {sender:14s} {a['n']:5d}  {fmt(a['full_record_exact']):>8s} "
          f"{fmt(b['full_record_exact']) if b else '       -':>8s} "
          f"{delta(a['full_record_exact'], b['full_record_exact']) if b else '':>7s}   "
          f"{fmt(a['tx_f1']):>6s} {fmt(b['tx_f1']) if b else '     -':>6s} "
          f"{delta(a['tx_f1'], b['tx_f1']) if b else '':>7s}\n")


def main():
    ap = argparse.ArgumentParser(description="Compare v1 sklearn against v2 MARBERT.")
    ap.add_argument("--splits", default="random",
                    help="comma-separated: " + ",".join(dataset.SPLITS))
    ap.add_argument("--runs", default=os.path.join(HERE, "runs"),
                    help="where train.py put the v2 checkpoints")
    ap.add_argument("--v1-only", action="store_true",
                    help="baseline table only; needs no torch and no checkpoints")
    ap.add_argument("--v2-only", action="store_true")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--data", default=dataset.DEFAULT_DATA)
    ap.add_argument("--manifest", default=dataset.DEFAULT_MANIFEST)
    ap.add_argument("--report", default=os.path.join(HERE, "compare_report.txt"))
    ap.add_argument("--json", default=os.path.join(HERE, "compare_results.json"))
    args = ap.parse_args()

    from evaluate import breakdown, score         # v1's own scorer — metric parity

    data, man = dataset.load(args.data, args.manifest)
    results = {}
    lines = []

    class Tee:
        def write(self, s):
            sys.stdout.write(s)
            lines.append(s)

    out = Tee()
    out.write("v1 (sms_eval_final, TF-IDF + 4x logistic regression)  vs"
              "  v2 (sms_v2, MARBERT gate + MARBERT multi-task extractor)\n")
    out.write(f"same train/test rows per split, both graded by evaluate.py:score()\n")

    for name in args.splits.split(","):
        name = name.strip()
        train, test = dataset.split(data, man, name, args.seed)
        out.write(f"\n\n### split {name}: {len(train)} train / {len(test)} test\n")

        r1 = b1 = None
        if not args.v2_only:
            t0 = time.time()
            pairs1 = v1_predictions(train, test)
            r1, _ = score(pairs1)
            b1 = breakdown(pairs1, lambda r: r["sender"])
            out.write(f"v1 trained + scored in {time.time() - t0:.1f}s\n")

        r2 = b2 = None
        if not args.v1_only:
            run_dir = os.path.join(args.runs, name)
            if not os.path.isdir(run_dir):
                out.write(f"\n  !! no v2 checkpoint at {run_dir}\n"
                          f"     train it:  python train.py --split {name} --stage both\n"
                          f"     (or re-run with --v1-only for the baseline alone)\n")
            else:
                t0 = time.time()
                pairs2 = v2_predictions(run_dir, test, args.device)
                r2, _ = score(pairs2)
                b2 = breakdown(pairs2, lambda r: r["sender"])
                out.write(f"v2 loaded + scored in {time.time() - t0:.1f}s\n")

        if r1 is None and r2 is None:
            continue
        results[name] = {"n_train": len(train), "n_test": len(test),
                         "v1": r1, "v2": r2,
                         "v1_by_sender": b1, "v2_by_sender": b2}
        if r1 is None:                            # --v2-only: one column, labelled as v2
            table(name, r2, None, out, labels=("v2 MARBERT", ""))
            sender_table(name, b2, None, out)
        else:
            table(name, r1, r2, out)
            sender_table(name, b1, b2, out)

    with open(args.json, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=1, default=str)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write("".join(lines))
    print(f"\nwrote {os.path.basename(args.report)} and {os.path.basename(args.json)}")


if __name__ == "__main__":
    main()
