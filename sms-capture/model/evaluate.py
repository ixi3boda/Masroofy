#!/usr/bin/env python3
"""Evaluate SmsTxnModel under three splits:
  random       5-fold random split (optimistic: same templates appear in train and test)
  unseen_wording  GroupKFold by template wording: test messages use wordings never seen in training
  unseen_sender   leave-one-sender-out: test sender's whole format never seen in training
Usage: python3 evaluate.py sms_dataset_1000.jsonl manifest.csv
"""
import json, csv, sys
from collections import defaultdict, Counter
from sklearn.model_selection import KFold, GroupKFold, LeaveOneGroupOut
from sms_model import SmsTxnModel

data = [json.loads(l) for l in open(sys.argv[1], encoding="utf-8")]
man = {int(r["id"]): r for r in csv.DictReader(open(sys.argv[2], encoding="utf-8-sig"))}
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
                    ok_all = False; errors[f].append((r["id"], g[f], p[f]))
            full += ok_all
        elif gt != pt:
            errors["is_transaction"].append((r["id"], gt, pt))
    prec = tp / max(tp + fp, 1); rec = tp / max(tp + fn, 1)
    res = {"tx_precision": prec, "tx_recall": rec, "tx_f1": 2 * prec * rec / max(prec + rec, 1e-9),
           "full_record_exact": full / max(tp + fn, 1)}
    res.update({f: fc[f] / max(ft[f], 1) for f in FIELDS})
    return res, errors

def run(split_name, splitter, groups=None):
    pairs = []
    idx = list(range(len(data)))
    for tr, te in splitter.split(idx, groups=groups, **({} if groups is None else {})):
        m = SmsTxnModel().fit([data[i] for i in tr])
        pairs += [(data[i], m.predict(data[i]["sms"])) for i in te]
    return score(pairs) + (pairs,)

if __name__ == "__main__":
    tmpl = [man[r["id"]]["template_id"] for r in data]
    send = [r["sender"] for r in data]
    out = {}
    for name, spl, g in [("random", KFold(5, shuffle=True, random_state=0), None),
                         ("unseen_wording", GroupKFold(5), tmpl),
                         ("unseen_sender", LeaveOneGroupOut(), send)]:
        res, errs, pairs = run(name, spl, g)
        out[name] = res
        print(f"\n=== {name}")
        for k, v in res.items(): print(f"  {k:18s} {v:.3f}")
        json.dump({k: v[:15] for k, v in errs.items()}, open(f"errors_{name}.json", "w", encoding="utf-8"),
                  ensure_ascii=False, indent=1, default=str)
        if name == "unseen_sender":   # per-sender breakdown
            per = defaultdict(list)
            for r, p in pairs: per[r["sender"]].append((r, p))
            out["unseen_sender_by_sender"] = {}
            for s, ps in per.items():
                rs, _ = score(ps); out["unseen_sender_by_sender"][s] = rs
                print(f"  [{s:12s}] tx_f1={rs['tx_f1']:.2f} amount={rs['amount']:.2f} type={rs['type']:.2f} "
                      f"merchant={rs['merchant']:.2f} full={rs['full_record_exact']:.2f}")
    json.dump(out, open("eval_results.json", "w"), indent=1)
