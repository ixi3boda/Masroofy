#!/usr/bin/env python3
"""Evaluate SmsTxnModel under four splits:
  random          5-fold random split (optimistic: same templates appear in train and test)
  unseen_wording  GroupKFold by template: test messages use wordings never seen in training
  unseen_sender   leave-one-sender-out: the test sender's whole format is never seen in training
  real_formats    train on the fictional-sender messages only, test on the real-format messages
                  (closest to production: the model meets real bank/wallet SMS it has never seen)

Usage: python3 evaluate.py sms_dataset_2200.jsonl manifest_2200.csv [--splits random,unseen_sender] [--jobs N]
The manifest needs id, template_id; optional provenance (fictional / verified / approximate).
Outputs: eval_results.json, errors_<split>.json (up to 15 examples per field, with the SMS text).
"""
import csv, json, sys
from collections import defaultdict, Counter
from joblib import Parallel, delayed
from sklearn.model_selection import KFold, GroupKFold, LeaveOneGroupOut
from sms_model import SmsTxnModel

FIELDS = ["type", "amount", "currency", "fee", "balance_after", "merchant", "channel", "datetime", "account_last4"]

def eq(a, b):
    if isinstance(a, float) and isinstance(b, float): return abs(a - b) < 1e-6
    return a == b

def score(pairs):
    tp = fp = fn = tn = 0; fc = Counter(); ft = Counter(); full = 0; errors = defaultdict(list)
    for r, p in pairs:
        g = r["expected"]; gt, pt = g["is_transaction"], p["is_transaction"]
        tp += gt and pt; fp += (not gt) and pt; fn += gt and not pt; tn += (not gt) and not pt
        if gt and pt:
            ok_all = True
            for f in FIELDS:
                ft[f] += 1
                if eq(g[f], p[f]): fc[f] += 1
                else:
                    ok_all = False; errors[f].append((r, g[f], p[f]))
            full += ok_all
        elif gt != pt:
            errors["is_transaction"].append((r, gt, pt))
    prec = tp / max(tp + fp, 1); rec = tp / max(tp + fn, 1)
    res = {"n": len(pairs), "tx_precision": prec, "tx_recall": rec, "tx_f1": 2 * prec * rec / max(prec + rec, 1e-9),
           # share of real non-transactions (OTP, promo, decline...) correctly rejected; None if the group has none
           "non_tx_rejected": tn / (tn + fp) if tn + fp else None,
           "full_record_exact": full / max(tp + fn, 1)}
    res.update({f: fc[f] / max(ft[f], 1) for f in FIELDS})
    return res, errors

def _fold(train, test):
    m = SmsTxnModel().fit(train)
    return [(r, m.predict(r["sms"])) for r in test]

def run(data, folds, jobs):
    out = Parallel(n_jobs=jobs)(delayed(_fold)([data[i] for i in tr], [data[i] for i in te]) for tr, te in folds)
    return [p for fold in out for p in fold]

def fmt(v): return "     -" if v is None else "%6.3f" % v

def breakdown(pairs, key_fn):
    groups = defaultdict(list)
    for r, p in pairs: groups[key_fn(r)].append((r, p))
    return {k: score(v)[0] for k, v in sorted(groups.items())}

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    opt = dict(zip(sys.argv[1::1], sys.argv[2::1]))
    splits = opt.get("--splits", "random,unseen_wording,unseen_sender,real_formats").split(",")
    jobs = int(opt.get("--jobs", -1))
    args = [a for a in args if a not in (opt.get("--splits"), opt.get("--jobs"))]

    data = [json.loads(l) for l in open(args[0], encoding="utf-8") if l.strip()]
    man = {int(r["id"]): r for r in csv.DictReader(open(args[1], encoding="utf-8-sig"))}
    prov = lambda r: man[r["id"]].get("provenance") or "fictional"
    idx = list(range(len(data)))
    tmpl = [man[r["id"]]["template_id"] for r in data]
    send = [r["sender"] for r in data]

    def folds(name):
        if name == "random": return list(KFold(5, shuffle=True, random_state=0).split(idx))
        if name == "unseen_wording": return list(GroupKFold(5).split(idx, groups=tmpl))
        if name == "unseen_sender": return list(LeaveOneGroupOut().split(idx, groups=send))
        if name == "real_formats":
            tr = [i for i in idx if prov(data[i]) == "fictional"]; te = [i for i in idx if prov(data[i]) != "fictional"]
            if not tr or not te: sys.exit("real_formats split needs a provenance column with fictional and real rows")
            return [(tr, te)]
        sys.exit("unknown split " + name)

    out = {}
    for name in splits:
        pairs = run(data, folds(name), jobs)
        res, errs = score(pairs)
        out[name] = res
        out[name + "_by_provenance"] = breakdown(pairs, prov)
        out[name + "_by_sender"] = breakdown(pairs, lambda r: r["sender"])
        print(f"\n=== {name}  (n={res['n']})")
        for k, v in res.items():
            if k != "n": print(f"  {k:18s} {fmt(v)}")
        print("  by provenance:   " + "  ".join(f"{p}: full={r['full_record_exact']:.2f} tx_f1={r['tx_f1']:.2f}"
                                             for p, r in out[name + "_by_provenance"].items()))
        print("  by sender:")
        for s, rs in out[name + "_by_sender"].items():
            print(f"    [{s:12s}] n={rs['n']:4d} tx_f1={rs['tx_f1']:.2f} rejected={fmt(rs['non_tx_rejected'])} "
                  f"amount={rs['amount']:.2f} type={rs['type']:.2f} merchant={rs['merchant']:.2f} "
                  f"datetime={rs['datetime']:.2f} full={rs['full_record_exact']:.2f}")
        json.dump({f: [{"id": r["id"], "sender": r["sender"], "template_id": man[r["id"]]["template_id"],
                        "gold": g, "pred": p, "sms": r["sms"]} for r, g, p in v[:15]] for f, v in errs.items()},
                  open(f"errors_{name}.json", "w", encoding="utf-8"), ensure_ascii=False, indent=1, default=str)
    json.dump(out, open("eval_results.json", "w"), indent=1)
