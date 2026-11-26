"""Field-level extraction metrics, used for BOTH standalone extraction and the
end-to-end pipeline (end_to_end_metrics.py decides which messages count).

Value equality is v1's own rule (sms_eval_final/evaluate.py:eq): floats within
1e-6, everything else exact. "Missing" is None on either side.

Per field
  accuracy   share of messages where predicted == gold (both None counts as
             correct: correctly reporting a field as absent is right)
For fields that are often absent (counterparty, fee, balance, last4, date), the
P/R/F1 view is more informative:
  tp  predicted a value, it equals gold
  fp  predicted a value, gold is None or different
  fn  gold has a value, predicted None or different
  precision = tp/(tp+fp), recall = tp/(tp+fn)

Record level
  full_record_exact   all 9 of v1's graded fields equal (what evaluate.py calls
                      full_record_exact; type and channel included)
  core_record_exact   amount, currency, counterparty, date, direction, last4
"""
import os
import sys

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from extraction.base import DIRECTION, V1_FIELDS            # noqa: E402

PRF_FIELDS = ["amount", "currency", "merchant", "date", "datetime", "direction", "type",
              "channel", "account_last4", "fee", "balance_after"]
CORE_FIELDS = ["amount", "currency", "merchant", "date", "direction", "account_last4"]


def eq(a, b):
    if isinstance(a, (int, float)) and isinstance(b, (int, float)) \
            and not isinstance(a, bool) and not isinstance(b, bool):
        return abs(float(a) - float(b)) < 1e-6
    return a == b


def derived(v1rec):
    """v1-schema record (gold or predicted) -> dict with the derived fields too."""
    d = {k: v1rec.get(k) for k in V1_FIELDS}
    dt_ = v1rec.get("datetime")
    d["date"] = dt_[:10] if dt_ else None
    d["direction"] = DIRECTION.get(v1rec.get("type")) if v1rec.get("is_transaction") else None
    return d


def field_scores(pairs):
    """pairs: list of (gold_v1_record, predicted_v1_record_or_None).

    A None prediction means "no record produced" (a missed transaction in the
    end-to-end view): every gold value then counts as a false negative."""
    n = len(pairs)
    out = {"n": n}
    acc = {f: 0 for f in PRF_FIELDS}
    prf = {f: [0, 0, 0] for f in PRF_FIELDS}
    full = core = 0
    for gold, pred in pairs:
        g = derived(gold)
        p = derived(pred) if pred is not None else {k: None for k in g}
        for f in PRF_FIELDS:
            gv, pv = g.get(f), p.get(f)
            same = eq(gv, pv)
            acc[f] += same
            if pv is not None and same:
                prf[f][0] += 1
            else:
                if pv is not None:
                    prf[f][1] += 1
                if gv is not None:
                    prf[f][2] += 1
        if pred is not None:
            full += all(eq(g[f], p[f]) for f in V1_FIELDS)
            core += all(eq(g[f], p[f]) for f in CORE_FIELDS)
    out["accuracy"] = {f: acc[f] / n if n else None for f in PRF_FIELDS}
    out["prf"] = {}
    for f, (tp, fp, fn) in prf.items():
        p_ = tp / (tp + fp) if tp + fp else None
        r_ = tp / (tp + fn) if tp + fn else None
        out["prf"][f] = {"tp": tp, "fp": fp, "fn": fn, "precision": p_, "recall": r_,
                         "f1": (2 * p_ * r_ / (p_ + r_)) if p_ and r_ else 0.0}
    out["full_record_exact"] = full / n if n else None
    out["core_record_exact"] = core / n if n else None
    return out


def headline(fs):
    a, p = fs["accuracy"], fs["prf"]
    return {"amount_acc": a["amount"], "currency_acc": a["currency"],
            "counterparty_precision": p["merchant"]["precision"],
            "counterparty_recall": p["merchant"]["recall"],
            "counterparty_f1": p["merchant"]["f1"],
            "date_acc": a["date"], "datetime_acc": a["datetime"],
            "direction_acc": a["direction"], "type_acc": a["type"],
            "account_last4_acc": a["account_last4"],
            "full_record_exact": fs["full_record_exact"],
            "core_record_exact": fs["core_record_exact"]}
