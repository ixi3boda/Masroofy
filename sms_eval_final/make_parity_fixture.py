#!/usr/bin/env python3
"""After retraining + exporting, regenerate the Java parity-test fixture from the Python model.
Usage: python3 make_parity_fixture.py sms_txn_model.joblib sms_dataset_1000.jsonl ../backend/src/test/resources/sms/parity_fixture.tsv"""
import json, sys
from sms_model import SmsTxnModel

def esc(s): return s.replace("\\", "\\\\").replace("\t", "\\t").replace("\n", "\\n").replace("\r", "\\r")
F = ["is_transaction", "type", "amount", "currency", "fee", "balance_after", "merchant", "channel", "datetime", "account_last4", "_confidence"]
m = SmsTxnModel.load(sys.argv[1])
rows = [json.loads(l) for l in open(sys.argv[2], encoding="utf-8") if l.strip()]
with open(sys.argv[3], "w", encoding="utf-8") as f:
    f.write("# id\tsms\t" + "\t".join(F) + "   (expected = Python model output; regenerate after retraining)\n")
    for r in rows:
        p = m.predict(r["sms"])
        vals = ["null" if p.get(k) is None else (str(p[k]).lower() if isinstance(p[k], bool) else str(p[k])) for k in F]
        f.write("\t".join([str(r["id"]), esc(r["sms"])] + [esc(v) for v in vals]) + "\n")
print("wrote", len(rows), "rows to", sys.argv[3])
