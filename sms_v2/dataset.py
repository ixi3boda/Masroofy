"""Loading, splits and token-label construction.

The splits are the point of this file. sms_eval_final/evaluate.py cross-validates
(5-fold, GroupKFold, leave-one-sender-out = 30 fits), which is fine for a 12-second
sklearn fit and impossible for a transformer. So v2 defines ONE train/test division
per regime, with the same intent as v1's folds, and compare.py trains BOTH
implementations on that exact division. The absolute numbers therefore differ from
eval_report.txt; the v1-vs-v2 delta is what is meaningful.

    python dataset.py splits                 # row counts per split
    python dataset.py coverage               # can we even label each gold field?
"""
import csv
import json
import os
import random
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spans
from schema import SPAN_TAGS, TOKEN_LABEL_ID, IGNORE_INDEX

HERE = os.path.dirname(os.path.abspath(__file__))
V1_DIR = os.path.normpath(os.path.join(HERE, "..", "sms_eval_final"))
DEFAULT_DATA = os.path.join(V1_DIR, "sms_dataset_2200.jsonl")
DEFAULT_MANIFEST = os.path.join(V1_DIR, "manifest_2200.csv")

SPLITS = ["random", "unseen_wording", "unseen_sender", "real_formats"]

# Held out for `unseen_sender`: one wallet, one state bank, one foreign bank and one
# fictional sender, ~20% of rows. Fixed rather than random so runs are comparable.
HELD_OUT_SENDERS = ["VF-Cash", "CIB", "HSBC", "NileBank"]


def load(data_path=DEFAULT_DATA, manifest_path=DEFAULT_MANIFEST):
    """-> (records, manifest_by_id). Records are v1's schema, untouched."""
    with open(data_path, encoding="utf-8") as f:
        data = [json.loads(l) for l in f if l.strip()]
    with open(manifest_path, encoding="utf-8-sig") as f:
        man = {int(r["id"]): r for r in csv.DictReader(f)}
    return data, man


def provenance(rec, man):
    return man[rec["id"]].get("provenance") or "fictional"


def split(data, man, name, seed=0):
    """-> (train_records, test_records)."""
    rng = random.Random(seed)
    idx = list(range(len(data)))

    if name == "random":
        rng.shuffle(idx)
        cut = int(len(idx) * 0.8)
        tr, te = idx[:cut], idx[cut:]

    elif name == "unseen_wording":
        groups = sorted({man[r["id"]]["template_id"] for r in data})
        rng.shuffle(groups)
        held = set(groups[:max(1, int(len(groups) * 0.2))])
        tr = [i for i in idx if man[data[i]["id"]]["template_id"] not in held]
        te = [i for i in idx if man[data[i]["id"]]["template_id"] in held]

    elif name == "unseen_sender":
        held = set(HELD_OUT_SENDERS)
        tr = [i for i in idx if data[i]["sender"] not in held]
        te = [i for i in idx if data[i]["sender"] in held]

    elif name == "real_formats":
        tr = [i for i in idx if provenance(data[i], man) == "fictional"]
        te = [i for i in idx if provenance(data[i], man) != "fictional"]

    else:
        raise SystemExit(f"unknown split {name!r}; pick one of {', '.join(SPLITS)}")

    if not tr or not te:
        raise SystemExit(f"split {name} produced an empty side")
    return [data[i] for i in tr], [data[i] for i in te]


# ------------------------------------------------------------------ token labels
def bio_from_spans(offsets, gold, special_mask=None):
    """Align character spans onto tokenizer offsets.

    offsets: list of (start, end) per token, (0, 0) for special tokens.
    gold:    {TAG: (start, end)} from spans.gold_spans().
    -> list of label ids, IGNORE_INDEX where the token is special.
    """
    labels = []
    started = set()
    for i, (a, b) in enumerate(offsets):
        if (special_mask and special_mask[i]) or a == b:
            labels.append(IGNORE_INDEX)
            continue
        tag = None
        for t in SPAN_TAGS:                      # SPAN_TAGS order breaks overlaps
            if t not in gold:
                continue
            s, e = gold[t]
            if a < e and b > s:                  # any overlap
                tag = t
                break
        if tag is None:
            labels.append(TOKEN_LABEL_ID["O"])
        else:
            prefix = "I" if tag in started else "B"
            started.add(tag)
            labels.append(TOKEN_LABEL_ID[f"{prefix}-{tag}"])
    return labels


def decode_bio(offsets, label_ids, text, id2label):
    """Inverse of bio_from_spans: -> {TAG: (start, end)} using the longest run per tag."""
    runs = {}
    cur_tag, cur_s, cur_e = None, None, None

    def flush():
        if cur_tag is None:
            return
        prev = runs.get(cur_tag)
        if prev is None or (cur_e - cur_s) > (prev[1] - prev[0]):
            runs[cur_tag] = (cur_s, cur_e)

    for (a, b), lid in zip(offsets, label_ids):
        if a == b:
            continue
        lab = id2label[int(lid)]
        if lab == "O":
            flush()
            cur_tag = None
            continue
        prefix, tag = lab.split("-", 1)
        if prefix == "B" or tag != cur_tag:
            flush()
            cur_tag, cur_s, cur_e = tag, a, b
        else:
            cur_e = b
    flush()
    return {t: (s, e) for t, (s, e) in runs.items() if text[s:e].strip()}


# ------------------------------------------------------------------ diagnostics
def coverage(data):
    """How many gold fields can the span layer actually locate?

    A field we cannot point at in the text is a field the token head cannot learn,
    so this is the ceiling on v2's extraction before any training happens.
    """
    tally = {t: [0, 0] for t in SPAN_TAGS}       # [found, present in gold]
    gold_key = {"AMOUNT": "amount", "FEE": "fee", "BALANCE": "balance_after",
                "LAST4": "account_last4", "MERCHANT": "merchant",
                "CURRENCY": "currency", "DATE": "datetime", "TIME": "datetime"}
    for r in data:
        exp = r["expected"]
        if not exp["is_transaction"]:
            continue
        got = spans.gold_spans(spans.bmp(r["sms"]), exp)
        for tag in SPAN_TAGS:
            key = gold_key[tag]
            present = exp.get(key) is not None and exp.get(key) != ""
            if tag == "TIME":
                present = bool(exp.get("datetime") and len(exp["datetime"]) > 10)
            if not present:
                continue
            tally[tag][1] += 1
            if tag in got:
                tally[tag][0] += 1
    return tally


def main():
    cmd = sys.argv[1] if len(sys.argv) > 1 else "splits"
    data, man = load()
    if cmd == "splits":
        print(f"{len(data)} records, {len({r['sender'] for r in data})} senders, "
              f"{len({man[r['id']]['template_id'] for r in data})} templates")
        print(f"\n{'split':16s} {'train':>7s} {'test':>7s}   test composition")
        for name in SPLITS:
            tr, te = split(data, man, name)
            senders = len({r["sender"] for r in te})
            tx = sum(r["expected"]["is_transaction"] for r in te)
            print(f"{name:16s} {len(tr):7d} {len(te):7d}   {senders} senders, "
                  f"{tx} tx / {len(te) - tx} non-tx")
    elif cmd == "coverage":
        tally = coverage(data)
        print("Share of gold fields the v2 span layer can locate in the text")
        print("(the ceiling on v2 extraction — an unlocatable field cannot be learned)\n")
        for tag, (found, total) in tally.items():
            pct = found / total if total else 0.0
            bar = "#" * int(pct * 30)
            print(f"  {tag:9s} {found:5d}/{total:<5d} {pct:6.1%} {bar}")
    else:
        raise SystemExit("usage: python dataset.py [splits|coverage]")


if __name__ == "__main__":
    main()
