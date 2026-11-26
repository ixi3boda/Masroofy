#!/usr/bin/env python3
"""Type an SMS, get the parsed transaction back.

    python try_sms.py                          # interactive
    python try_sms.py "تم خصم 250 جنيه ..."     # one message, then exit
    python try_sms.py --json --jsonl in.jsonl  # batch a dataset file

Commands inside the prompt:
    :paste   read a multi-line message, ending with a blank line (real bank SMS wrap)
    :json    toggle raw JSON output
    :q       quit (Ctrl-D / Ctrl-C also work)
"""
import argparse, json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)        # the .joblib pickles sms_model.SmsTxnModel by name

# A .joblib is a pickle of SmsTxnModel: it only loads under the scikit-learn it was
# trained with. The committed sms_txn_model.joblib came from 1.9.1, so prefer a locally
# trained sms_txn_model.local.joblib when one is there.
CANDIDATE_MODELS = ["sms_txn_model.local.joblib", "sms_txn_model.joblib"]

FIELDS = [("type", "type"), ("amount", "amount"), ("currency", "currency"), ("fee", "fee"),
          ("balance_after", "balance after"), ("merchant", "merchant"), ("channel", "channel"),
          ("datetime", "datetime"), ("account_last4", "account last4")]


def show(sms, p, as_json):
    if as_json:
        print(json.dumps({"sms": sms, "predicted": p}, ensure_ascii=False, indent=2))
        return
    conf = p.get("_confidence")
    if not p["is_transaction"]:
        reason = p.get("_reason", "classified as not a transaction")
        print(f"  not a transaction  ({reason}, confidence {conf})")
        return
    print(f"  TRANSACTION  (confidence {conf})")
    for key, label in FIELDS:
        v = p.get(key)
        print(f"    {label:<14} {'—' if v is None else v}")


def sklearn_version():
    try:
        import sklearn
        return sklearn.__version__
    except Exception:
        return "unknown"


def read_message(prompt):
    """One line, or a whole block after :paste. Returns None at EOF, '' to skip."""
    line = input(prompt)
    if line.strip() != ":paste":
        return line
    print("  (paste the message, then an empty line)")
    lines = []
    while True:
        try:
            nxt = input("  | ")
        except EOFError:
            break
        if not nxt.strip():
            break
        lines.append(nxt)
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description="Interactive SMS transaction parser.")
    ap.add_argument("sms", nargs="*", help="message(s) to parse, then exit")
    ap.add_argument("--model", default=None, help="path to a .joblib (default: the newest "
                    "of sms_txn_model.local.joblib, sms_txn_model.joblib)")
    ap.add_argument("--jsonl", metavar="FILE", help="parse every record in a dataset .jsonl")
    ap.add_argument("--json", action="store_true", help="print raw JSON instead of a field list")
    args = ap.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")      # Arabic on a Windows console

    path = args.model
    if path is None:
        found = [p for p in (os.path.join(HERE, m) for m in CANDIDATE_MODELS) if os.path.exists(p)]
        path = found[0] if found else os.path.join(HERE, CANDIDATE_MODELS[-1])
    if not os.path.exists(path):
        sys.exit(f"no model at {path}\n"
                 f"train one:  python sms_model.py train sms_dataset_2200.jsonl "
                 f"sms_txn_model.local.joblib")

    from sms_model import SmsTxnModel
    print(f"loading {os.path.basename(path)} ...", file=sys.stderr)
    try:
        model = SmsTxnModel.load(path)
        model.predict("test 1")      # a pickle from another sklearn fails here, not on load
    except Exception as e:
        sys.exit(f"{type(e).__name__}: {e}\n\n"
                 f"{os.path.basename(path)} was pickled by a different scikit-learn than the "
                 f"installed {sklearn_version()}.\nRetrain:  python sms_model.py train "
                 f"sms_dataset_2200.jsonl sms_txn_model.local.joblib")

    if args.jsonl:
        with open(args.jsonl, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                r = json.loads(line)
                print(json.dumps({"id": r.get("id"), "sms": r["sms"],
                                  "predicted": model.predict(r["sms"])}, ensure_ascii=False))
        return

    if args.sms:
        for sms in args.sms:
            show(sms, model.predict(sms), args.json)
        return

    as_json = args.json
    print("Type an SMS and press Enter.  :paste for multi-line,  :json to toggle,  :q to quit.\n")
    while True:
        try:
            sms = read_message("sms> ")
        except (EOFError, KeyboardInterrupt):
            print()
            return
        if sms is None or sms.strip() in (":q", ":quit", ":exit"):
            return
        if sms.strip() == ":json":
            as_json = not as_json
            print(f"  json output {'on' if as_json else 'off'}")
            continue
        if not sms.strip():
            continue
        try:
            show(sms, model.predict(sms), as_json)
        except Exception as e:                    # a bad message shouldn't kill the session
            print(f"  error: {type(e).__name__}: {e}")
        print()


if __name__ == "__main__":
    main()
