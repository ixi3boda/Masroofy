"""Load the corpus and attach the two Stage-1 label sets.

Returns plain dicts so nothing downstream depends on pandas:

    {"id", "sender", "sms", "expected", "category", "template_id", "provenance",
     "duplicate_group", "language",
     "label_binary", "label_multi", "label_reason"}

`expected` is v1's gold record, untouched; it is what extraction is graded on.
"""
import csv
import hashlib
import json
import os
import re
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
import spans                                     # noqa: E402
from config import labels as L                    # noqa: E402
from config import settings as S                  # noqa: E402

_RULES = [(cls, re.compile(rx, re.I)) for cls, rx in L.RULES]


class LabelError(ValueError):
    """The label configuration and the data disagree. Fix the config, never the data."""


def data_hash(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()[:16]


def multiclass_label(rec):
    """-> (class, reason). Reason says which config entry produced the class."""
    if rec["expected"]["is_transaction"]:
        return L.TRANSACTION, "gold is_transaction=True"
    cat = rec["category"]
    if cat in L.CATEGORY_MAP:
        cls = L.CATEGORY_MAP[cat]
        if cls == L.TRANSACTION:
            raise LabelError(f"id {rec['id']}: CATEGORY_MAP sends non-transaction category "
                             f"{cat!r} to 'transaction'")
        return cls, f"CATEGORY_MAP[{cat}]"
    if cat in L.MIXED_CATEGORIES:
        text = spans.normalize(rec["sms"])
        for cls, rx in _RULES:
            if rx.search(text):
                return cls, f"RULES[{cls}] in mixed category {cat}"
        return "other", f"no rule matched in mixed category {cat}"
    raise LabelError(f"id {rec['id']}: non-transaction in category {cat!r}, which is in "
                     "neither CATEGORY_MAP nor MIXED_CATEGORIES (config/labels.py)")


def load(data_path=None, manifest_path=None):
    """-> list of records with labels attached, in file order."""
    data_path = data_path or S.DATA_PATH
    manifest_path = manifest_path or S.MANIFEST_PATH
    with open(data_path, encoding="utf-8") as f:
        data = [json.loads(line) for line in f if line.strip()]
    with open(manifest_path, encoding="utf-8-sig") as f:
        man = {int(r["id"]): r for r in csv.DictReader(f)}

    missing = [r["id"] for r in data if r["id"] not in man]
    if missing:
        raise LabelError(f"{len(missing)} records have no manifest row, e.g. {missing[:5]}")
    ids = Counter(r["id"] for r in data)
    dup_ids = [i for i, c in ids.items() if c > 1]
    if dup_ids:
        raise LabelError(f"duplicate ids in data: {dup_ids[:5]}")

    out = []
    for r in data:
        m = man[r["id"]]
        rec = dict(r)
        rec["sms"] = r.get("sms") or ""
        rec["category"] = m.get("category", "")
        rec["template_id"] = m.get("template_id", "") or f"_id{r['id']}"
        rec["provenance"] = m.get("provenance") or "fictional"
        rec["duplicate_group"] = m.get("duplicate_group") or ""
        rec["language"] = m.get("language") or ""
        rec["label_binary"] = (L.TRANSACTION if r["expected"]["is_transaction"]
                               else L.NON_TRANSACTION)
        rec["label_multi"], rec["label_reason"] = multiclass_label(rec)
        out.append(rec)
    return out


def label_column(experiment):
    if experiment == "binary":
        return "label_binary"
    if experiment == "multiclass":
        return "label_multi"
    raise ValueError(f"unknown experiment {experiment!r}")


def class_list(experiment):
    return list(L.BINARY_CLASSES) if experiment == "binary" else list(L.CLASSES)


def validate(records):
    """Cross-checks between the derived labels and the gold data. -> list of problems."""
    problems = []
    for r in records:
        if r["label_multi"] not in L.CLASSES:
            problems.append(f"id {r['id']}: unknown class {r['label_multi']!r}")
        if (r["label_multi"] == L.TRANSACTION) != (r["label_binary"] == L.TRANSACTION):
            problems.append(f"id {r['id']}: binary and multi-class labels disagree")
        if r["label_binary"] == L.TRANSACTION and r["expected"].get("amount") is None:
            problems.append(f"id {r['id']}: gold transaction without an amount")
    by_text = {}
    for r in records:
        key = r["sms"]
        if key in by_text and by_text[key]["label_multi"] != r["label_multi"]:
            problems.append(f"ids {by_text[key]['id']} and {r['id']}: identical text, "
                            f"different labels")
        by_text.setdefault(key, r)
    return problems


def write_audit(records, out_dir=None):
    """label_audit.csv (every derived label + reason) and labels.csv (id -> labels)."""
    out_dir = out_dir or S.PROCESSED_DIR
    os.makedirs(out_dir, exist_ok=True)
    audit = os.path.join(out_dir, "label_audit.csv")
    with open(audit, "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "sender", "category", "template_id", "label_binary",
                    "label_multi", "label_reason", "sms"])
        for r in records:
            w.writerow([r["id"], r["sender"], r["category"], r["template_id"],
                        r["label_binary"], r["label_multi"], r["label_reason"], r["sms"]])
    lab = os.path.join(out_dir, "labels.csv")
    with open(lab, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "label_binary", "label_multi"])
        for r in records:
            w.writerow([r["id"], r["label_binary"], r["label_multi"]])
    return audit, lab
