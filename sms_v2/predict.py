"""Run the v2 pipeline and write records in the existing dataset's JSON shape.

    python predict.py --run runs/random "تم خصم 250 جنيه ..."
    python predict.py --run runs/random --jsonl inbox.jsonl --out db.jsonl
    python predict.py --run runs/random --jsonl inbox.jsonl --out db.jsonl --as-dataset

`--as-dataset` emits exactly sms_dataset_2200.jsonl's schema —
{"id", "sender", "sms", "expected": {...}} — so the output is a drop-in JSON
database: sms_eval_final/evaluate.py, make_parity_fixture.py and anything else that
reads the corpus will read it unchanged. Without the flag the fields go under
"predicted" instead, which is the right shape when you want to keep gold and
prediction side by side.

Input .jsonl may be the corpus schema, or just {"sms": ...} per line, or
{"sms":..., "sender":..., "id":...}.
"""
import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from schema import FIELDS

INTERNAL = ("_confidence", "_reason")


def clean(rec, keep_internal=False):
    out = {"is_transaction": rec["is_transaction"]}
    for f in FIELDS:
        out[f] = rec.get(f)
    if keep_internal:
        for k in INTERNAL:
            if k in rec:
                out[k] = rec[k]
    return out


def read_lines(path):
    with open(path, encoding="utf-8") as f:
        for i, line in enumerate(f, 1):
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:          # a plain-text inbox, one SMS per line
                r = {"sms": line}
            if "sms" not in r:
                raise SystemExit(f"{path}:{i} has no \"sms\" key")
            yield r


def main():
    ap = argparse.ArgumentParser(description="v2 pipeline -> JSON records.")
    ap.add_argument("sms", nargs="*", help="message(s) to parse")
    ap.add_argument("--run", default=None, help="checkpoint dir (default: runs/random)")
    ap.add_argument("--jsonl", help="input file, one record or one SMS per line")
    ap.add_argument("--out", help="output .jsonl (default: stdout)")
    ap.add_argument("--as-dataset", action="store_true",
                    help='emit the corpus schema with the prediction under "expected"')
    ap.add_argument("--start-id", type=int, default=1, help="id for inputs that have none")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--confidence", action="store_true", help="keep _confidence/_reason")
    args = ap.parse_args()

    here = os.path.dirname(os.path.abspath(__file__))
    run = args.run or os.path.join(here, "runs", "random")
    if not os.path.isdir(run):
        raise SystemExit(f"no checkpoint at {run}\ntrain one:  python train.py "
                         f"--split random --stage both")

    import pipeline
    pipe = pipeline.load(run, args.device)

    if args.jsonl:
        rows = list(read_lines(args.jsonl))
    elif args.sms:
        rows = [{"sms": s} for s in args.sms]
    else:
        rows = [{"sms": l.rstrip("\n")} for l in sys.stdin if l.strip()]
    if not rows:
        raise SystemExit("nothing to parse")

    preds = pipe.predict_many([r["sms"] for r in rows])

    key = "expected" if args.as_dataset else "predicted"
    sink = open(args.out, "w", encoding="utf-8") if args.out else sys.stdout
    try:
        if hasattr(sink, "reconfigure"):
            sink.reconfigure(encoding="utf-8")
    except Exception:
        pass
    try:
        for i, (r, p) in enumerate(zip(rows, preds)):
            rec = {"id": r.get("id", args.start_id + i),
                   "sender": r.get("sender", ""),
                   "sms": r["sms"],
                   key: clean(p, args.confidence)}
            sink.write(json.dumps(rec, ensure_ascii=False) + "\n")
    finally:
        if args.out:
            sink.close()
            n_tx = sum(p["is_transaction"] for p in preds)
            print(f"wrote {len(rows)} records to {args.out} "
                  f"({n_tx} transactions, {len(rows) - n_tx} rejected)")


if __name__ == "__main__":
    main()
