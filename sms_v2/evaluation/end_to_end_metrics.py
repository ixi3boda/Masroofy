"""End-to-end pipeline metrics over the WHOLE test set.

Each test message ends in one of four outcomes:

  correct_record   gold transaction, a record was produced
  missed           gold transaction, no record (Stage 1 rejected it, OR Stage 2
                   found no amount) -> counts against every field
  false_record     gold non-transaction, a record was produced -> a fabricated
                   financial entry
  correct_reject   gold non-transaction, no record

Nothing is computed on "correctly classified messages only". Field accuracy is
over ALL gold transactions, with a missed one scored as an all-null prediction,
and the record-level numbers count both kinds of error:

  e2e_full_exact_recall     exact records / gold transactions
  e2e_full_exact_precision  exact records / records produced
  e2e_full_exact_f1         harmonic mean of the two
"""
import os
import sys
from collections import Counter

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, HERE)
from evaluation import extraction_metrics as EM            # noqa: E402
from extraction.base import V1_FIELDS                      # noqa: E402


def compute(test_records, routed, outputs, require_amount=True):
    """test_records: gold records; routed: {id: bool}; outputs: {id: output record}.
    -> metrics dict, per-message outcome list."""
    from extraction.base import to_v1
    outcomes, pairs, false_by_class = [], [], Counter()
    exact = produced = 0
    for r in test_records:
        out = outputs[r["id"]]["output"]
        made = routed[r["id"]] and (out["extraction_ok"] or not require_amount)
        pred = to_v1(out) if made else None
        if made and pred["amount"] is None and not require_amount:
            pred["is_transaction"] = True
        gold_tx = r["expected"]["is_transaction"]
        if gold_tx:
            pairs.append((r["expected"], pred))
            ok = pred is not None and all(EM.eq(r["expected"][f], pred[f]) for f in V1_FIELDS)
            exact += ok
            outcome = "correct_record" if pred is not None else "missed"
        else:
            outcome = "false_record" if made else "correct_reject"
            if made:
                false_by_class[r["label_multi"]] += 1
        produced += made
        reason = None
        if gold_tx and not made:
            reason = "rejected by stage 1" if not routed[r["id"]] else "stage 2: no amount found"
        outcomes.append({"id": r["id"], "outcome": outcome, "reason": reason,
                         "exact": bool(gold_tx and pred is not None and
                                       all(EM.eq(r["expected"][f], pred[f]) for f in V1_FIELDS))})

    c = Counter(o["outcome"] for o in outcomes)
    n_gold = sum(1 for r in test_records if r["expected"]["is_transaction"])
    rec = exact / n_gold if n_gold else None
    prec = exact / produced if produced else None
    fs = EM.field_scores(pairs)
    missed_reasons = Counter(o["reason"] for o in outcomes if o["outcome"] == "missed")
    return {"n_messages": len(test_records), "n_gold_transactions": n_gold,
            "records_produced": produced,
            "correct_records": c["correct_record"], "missed_transactions": c["missed"],
            "false_records": c["false_record"], "correct_rejects": c["correct_reject"],
            "missed_by_reason": dict(missed_reasons),
            "false_records_by_class": dict(false_by_class),
            "e2e_full_exact_recall": rec, "e2e_full_exact_precision": prec,
            "e2e_full_exact_f1": (2 * rec * prec / (rec + prec)) if rec and prec else 0.0,
            "fields_over_all_gold_transactions": fs,
            "headline": EM.headline(fs)}, outcomes
