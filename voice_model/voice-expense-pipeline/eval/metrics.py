"""Field comparison rules and metric aggregation for the evaluation.

WHY these rules (also in docs/DECISIONS.md):
    * amount: equal within 0.01 (Decimal vs float noise).
    * currency, category, transaction_type, payment_method: exact.
    * merchant: same canonical gazetteer name; for names not in the
      gazetteer, rapidfuzz token_set_ratio >= 85 (so "Cafe Zooba" == "Zooba").
      Expected null + predicted null is correct.
    * date: exact ISO date.
    * time: exact, or within 60 minutes when the phrase used a time-of-day
      word ("الصبح" -> 09:00 is a convention, 08:30 is not really wrong).

The three numbers the project proposal asks for:
    1. "amount, date and merchant captured correctly" -> per-field accuracy
    2. "how often users need to correct a field"     -> correction rate
    3. "how long processing takes"                    -> latency (p50/p95)
"""
from __future__ import annotations

import math
import re
import statistics
import sys
from pathlib import Path
from typing import Any, Iterable, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice_expense import fuzzy  # noqa: E402
from voice_expense.merchants import get_gazetteer  # noqa: E402
from voice_expense.normalize import fold, normalize_text, tokenize  # noqa: E402

EVAL_FIELDS = ["transaction_type", "amount", "currency", "merchant", "category", "date", "time", "payment_method"]
KEY_FIELDS = ["amount", "currency", "merchant", "category", "date"]


# ---------------------------------------------------------------------------
# Field comparison
# ---------------------------------------------------------------------------
def _to_float(v: Any) -> Optional[float]:
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def compare_amount(expected: Any, predicted: Any) -> bool:
    e, p = _to_float(expected), _to_float(predicted)
    if e is None or p is None:
        return e is None and p is None
    return abs(e - p) <= 0.01


def compare_merchant(expected: Optional[str], predicted: Optional[str]) -> bool:
    if not expected or not predicted:
        return not expected and not predicted
    gaz = get_gazetteer()
    ce, cp = gaz.canonical(expected), gaz.canonical(predicted)
    if ce or cp:
        return (ce or expected).lower() == (cp or predicted).lower()
    return fuzzy.token_set_ratio(expected.lower(), predicted.lower()) >= 85


def _minutes(t: str) -> Optional[int]:
    m = re.fullmatch(r"(\d{1,2}):(\d{2})", t or "")
    if not m:
        return None
    return int(m.group(1)) * 60 + int(m.group(2))


def compare_time(expected: Optional[str], predicted: Optional[str], tolerant: bool = False) -> bool:
    if not expected or not predicted:
        return not expected and not predicted
    e, p = _minutes(expected), _minutes(predicted)
    if e is None or p is None:
        return False
    if tolerant:
        return abs(e - p) <= 60
    return e == p


def compare_field(field: str, expected: Any, predicted: Any, tags: Iterable[str] = ()) -> bool:
    if field == "amount":
        return compare_amount(expected, predicted)
    if field == "merchant":
        return compare_merchant(expected, predicted)
    if field == "time":
        return compare_time(expected, predicted, tolerant="time_word" in set(tags))
    if field == "date":
        return str(expected) == str(predicted)
    if expected is None or predicted is None:
        return expected is None and predicted is None
    return str(expected).strip().lower() == str(predicted).strip().lower()


# ---------------------------------------------------------------------------
# ASR error rates
# ---------------------------------------------------------------------------
def normalize_for_wer(text: str) -> str:
    """Same normalization for reference and hypothesis: digits, alef, ta marbuta, punctuation, case."""
    return " ".join(fold(t.text) for t in tokenize(normalize_text(text or "")))


def _edit_distance(a: list[str], b: list[str]) -> int:
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i] + [0] * len(b)
        for j, y in enumerate(b, 1):
            cur[j] = min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y))
        prev = cur
    return prev[-1]


def wer(reference: str, hypothesis: str) -> float:
    r, h = normalize_for_wer(reference), normalize_for_wer(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    try:
        import jiwer  # type: ignore

        return float(jiwer.wer(r, h if h else "<empty>"))
    except Exception:
        rw, hw = r.split(), h.split()
        return _edit_distance(rw, hw) / max(1, len(rw))


def cer(reference: str, hypothesis: str) -> float:
    r, h = normalize_for_wer(reference), normalize_for_wer(hypothesis)
    if not r:
        return 0.0 if not h else 1.0
    try:
        import jiwer  # type: ignore

        return float(jiwer.cer(r, h if h else " "))
    except Exception:
        return _edit_distance(list(r), list(h)) / max(1, len(r))


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
def pct(num: float, den: float) -> float:
    return round(100.0 * num / den, 1) if den else float("nan")


def percentile(values: list[float], q: float) -> float:
    if not values:
        return float("nan")
    s = sorted(values)
    k = (len(s) - 1) * q
    lo, hi = math.floor(k), math.ceil(k)
    if lo == hi:
        return s[int(k)]
    return s[lo] + (s[hi] - s[lo]) * (k - lo)


def latency_stats(values: list[float]) -> dict[str, float]:
    if not values:
        return {"mean": float("nan"), "p50": float("nan"), "p95": float("nan"), "n": 0}
    return {
        "mean": round(statistics.fmean(values), 2),
        "p50": round(percentile(values, 0.5), 2),
        "p95": round(percentile(values, 0.95), 2),
        "n": len(values),
    }


def score_record(expected: dict[str, Any], predicted: dict[str, Any], tags: Iterable[str]) -> dict[str, bool]:
    return {f: compare_field(f, expected.get(f), predicted.get(f), tags) for f in EVAL_FIELDS}


def aggregate(records: list[dict[str, Any]]) -> dict[str, Any]:
    """records: [{"lang_group", "difficulty", "correct": {field: bool}, "needs_review": [...]}, ...]"""
    out: dict[str, Any] = {"n": len(records)}

    def field_acc(rs: list[dict[str, Any]]) -> dict[str, float]:
        return {f: pct(sum(r["correct"][f] for r in rs), len(rs)) for f in EVAL_FIELDS}

    out["field_accuracy"] = field_acc(records)
    out["by_lang"] = {g: field_acc([r for r in records if r["lang_group"] == g])
                      for g in sorted({r["lang_group"] for r in records})}
    out["by_difficulty"] = {d: field_acc([r for r in records if r["difficulty"] == d])
                            for d in ("easy", "medium", "hard") if any(r["difficulty"] == d for r in records)}

    def exact(rs: list[dict[str, Any]]) -> float:
        return pct(sum(all(r["correct"][f] for f in KEY_FIELDS) for r in rs), len(rs))

    out["exact_match"] = exact(records)
    out["exact_match_by_lang"] = {g: exact([r for r in records if r["lang_group"] == g]) for g in out["by_lang"]}

    def corrections(rs: list[dict[str, Any]]) -> dict[str, float]:
        wrong_counts = [sum(not r["correct"][f] for f in EVAL_FIELDS) for r in rs]
        return {
            "avg_fields_to_fix": round(sum(wrong_counts) / len(rs), 3) if rs else float("nan"),
            "pct_needing_fix": pct(sum(c > 0 for c in wrong_counts), len(rs)),
        }

    out["correction"] = corrections(records)
    out["correction_by_lang"] = {g: corrections([r for r in records if r["lang_group"] == g]) for g in out["by_lang"]}

    flagged = wrong = flagged_wrong = 0
    for r in records:
        for f in EVAL_FIELDS:
            is_flag = f in r.get("needs_review", [])
            is_wrong = not r["correct"][f]
            flagged += is_flag
            wrong += is_wrong
            flagged_wrong += is_flag and is_wrong
    out["review_precision"] = pct(flagged_wrong, flagged)
    out["review_recall"] = pct(flagged_wrong, wrong)
    out["review_f1"] = f1_pct(out["review_precision"], out["review_recall"])
    out["review_counts"] = {"flagged": flagged, "wrong": wrong, "flagged_and_wrong": flagged_wrong}

    # Precision / recall / F1 (only when expected/predicted values were stored in the records)
    if records and "expected" in records[0]:
        out["slot_prf"] = slot_prf(records)
        out["slot_prf_by_lang"] = {g: slot_prf([r for r in records if r["lang_group"] == g]) for g in out["by_lang"]}
        out["category_report"] = classification_report(
            [str(r["expected"].get("category")) for r in records], [str(r["predicted"].get("category")) for r in records])
        out["transaction_type_report"] = classification_report(
            [str(r["expected"].get("transaction_type")) for r in records],
            [str(r["predicted"].get("transaction_type")) for r in records])
        out["payment_report"] = classification_report(
            [str(r["expected"].get("payment_method")) for r in records],
            [str(r["predicted"].get("payment_method")) for r in records])
    return out


# ---------------------------------------------------------------------------
# Precision / recall / F1
# ---------------------------------------------------------------------------
# Values that mean "nothing was extracted" for a field.
EMPTY_VALUES: dict[str, set[Any]] = {"payment_method": {"unknown"}}


def is_empty(field: str, value: Any) -> bool:
    return value is None or value == "" or value in EMPTY_VALUES.get(field, set())


def f1_pct(p: float, r: float) -> float:
    if p != p or r != r:  # NaN
        return float("nan")
    return round(2 * p * r / (p + r), 1) if (p + r) else 0.0


def slot_prf(records: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    """Slot-filling precision/recall/F1 per field (the standard way to score information extraction).

    For each example and field:
      * TP: something was predicted and it is correct
      * FP: something was predicted but it is wrong, or nothing was expected
      * FN: something was expected but the prediction is empty or wrong
      * TN: nothing expected and nothing predicted
    A wrong value counts as both FP and FN (it is a wrong answer AND a missed right answer).
    precision = TP/(TP+FP): "when the system fills a field, how often is it right?"
    recall    = TP/(TP+FN): "of the fields that should be filled, how many did it get right?"
    F1        = harmonic mean of the two. "micro" = all fields pooled together.
    """
    out: dict[str, dict[str, float]] = {}
    tot = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}
    for f in EVAL_FIELDS:
        tp = fp = fn = tn = 0
        for r in records:
            exp_v, pred_v = r["expected"].get(f), r["predicted"].get(f)
            e_empty, p_empty = is_empty(f, exp_v), is_empty(f, pred_v)
            ok = r["correct"][f]
            if e_empty and p_empty:
                tn += 1
            elif p_empty:
                fn += 1
            elif e_empty:
                fp += 1
            elif ok:
                tp += 1
            else:
                fp += 1
                fn += 1
        p, rc = pct(tp, tp + fp), pct(tp, tp + fn)
        out[f] = {"accuracy": pct(sum(r["correct"][f] for r in records), len(records)),
                  "precision": p, "recall": rc, "f1": f1_pct(p, rc), "tp": tp, "fp": fp, "fn": fn, "tn": tn}
        for k, v in (("tp", tp), ("fp", fp), ("fn", fn), ("tn", tn)):
            tot[k] += v
    p, rc = pct(tot["tp"], tot["tp"] + tot["fp"]), pct(tot["tp"], tot["tp"] + tot["fn"])
    out["micro"] = {"accuracy": pct(sum(sum(r["correct"].values()) for r in records), len(records) * len(EVAL_FIELDS)),
                    "precision": p, "recall": rc, "f1": f1_pct(p, rc), **tot}
    return out


def classification_report(y_true: list[str], y_pred: list[str]) -> dict[str, Any]:
    """Per-class precision/recall/F1 + macro and weighted averages + confusion matrix (like scikit-learn)."""
    labels = sorted(set(y_true) | set(y_pred))
    per: dict[str, dict[str, float]] = {}
    for c in labels:
        tp = sum(t == c and p == c for t, p in zip(y_true, y_pred))
        fp = sum(t != c and p == c for t, p in zip(y_true, y_pred))
        fn = sum(t == c and p != c for t, p in zip(y_true, y_pred))
        prec, rec = pct(tp, tp + fp), pct(tp, tp + fn)
        per[c] = {"precision": prec, "recall": rec, "f1": f1_pct(prec, rec), "support": sum(t == c for t in y_true)}

    def _avg(key: str, weighted: bool) -> float:
        rows = [(v[key], v["support"]) for v in per.values() if v["support"] > 0 and v[key] == v[key]]
        if not rows:
            return float("nan")
        if weighted:
            total = sum(s for _, s in rows)
            return round(sum(x * s for x, s in rows) / total, 1) if total else float("nan")
        return round(sum(x for x, _ in rows) / len(rows), 1)

    matrix = {t: {p: sum(a == t and b == p for a, b in zip(y_true, y_pred)) for p in labels} for t in labels}
    return {
        "labels": labels,
        "per_class": per,
        "accuracy": pct(sum(t == p for t, p in zip(y_true, y_pred)), len(y_true)),
        "macro": {k: _avg(k, False) for k in ("precision", "recall", "f1")},
        "weighted": {k: _avg(k, True) for k in ("precision", "recall", "f1")},
        "confusion": matrix,
    }
