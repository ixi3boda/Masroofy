"""Field comparison rules and aggregation used by eval/evaluate.py."""
from __future__ import annotations

from eval.metrics import aggregate, cer, compare_field, latency_stats, wer


def test_amount_tolerance() -> None:
    assert compare_field("amount", 150, "150.00")
    assert compare_field("amount", 10.5, 10.509)
    assert not compare_field("amount", 150, 151)
    assert compare_field("amount", None, None)
    assert not compare_field("amount", None, 5)


def test_merchant_rules() -> None:
    assert compare_field("merchant", "Uber", "أوبر")
    assert compare_field("merchant", "Cafe Zooba", "zooba cafe")
    assert not compare_field("merchant", "Uber", "Careem")
    assert compare_field("merchant", None, None)
    assert not compare_field("merchant", None, "Uber")


def test_time_rules() -> None:
    assert compare_field("time", "09:00", "09:00")
    assert not compare_field("time", "09:00", "09:30")
    assert compare_field("time", "09:00", "09:45", tags=["time_word"])
    assert not compare_field("time", "09:00", "11:00", tags=["time_word"])


def test_exact_fields() -> None:
    assert compare_field("category", "groceries", "groceries")
    assert not compare_field("currency", "EGP", "USD")
    assert compare_field("date", "2026-11-19", "2026-11-19")


def test_wer_cer_normalized() -> None:
    assert wer("دفعت ١٥٠ جنيه", "دفعت 150 جنيه") == 0.0
    assert wer("دفعت 150 جنيه", "دفعت 150") > 0
    assert cer("قهوة", "قهوه") == 0.0


def test_aggregate_and_correction_rate() -> None:
    fields = ["transaction_type", "amount", "currency", "merchant", "category", "date", "time", "payment_method"]
    ok = {f: True for f in fields}
    bad = dict(ok, amount=False, merchant=False)
    recs = [
        {"lang_group": "ar", "difficulty": "easy", "correct": ok, "needs_review": []},
        {"lang_group": "en", "difficulty": "hard", "correct": bad, "needs_review": ["amount"]},
    ]
    agg = aggregate(recs)
    assert agg["field_accuracy"]["amount"] == 50.0
    assert agg["exact_match"] == 50.0
    assert agg["correction"]["avg_fields_to_fix"] == 1.0
    assert agg["correction"]["pct_needing_fix"] == 50.0
    assert agg["review_precision"] == 100.0 and agg["review_recall"] == 50.0


def test_latency_stats() -> None:
    s = latency_stats([1.0, 2.0, 3.0, 4.0, 100.0])
    assert s["p50"] == 3.0 and s["n"] == 5 and s["p95"] > 4.0


def _rec(exp: dict, pred: dict, lang: str = "ar") -> dict:
    from eval.metrics import score_record

    full = {"transaction_type": "expense", "amount": None, "currency": "EGP", "merchant": None, "category": "other",
            "date": "2026-11-20", "time": None, "payment_method": "unknown"}
    e, p = dict(full, **exp), dict(full, **pred)
    return {"lang_group": lang, "difficulty": "easy", "correct": score_record(e, p, []), "needs_review": [],
            "expected": e, "predicted": p}


def test_slot_precision_recall_f1() -> None:
    from eval.metrics import slot_prf

    recs = [
        _rec({"amount": 100}, {"amount": 100}),      # TP
        _rec({"amount": 100}, {"amount": 200}),      # wrong -> FP + FN
        _rec({"amount": 100}, {"amount": None}),     # missed -> FN
        _rec({"amount": None}, {"amount": 50}),      # invented -> FP
        _rec({"amount": None}, {"amount": None}),    # TN
    ]
    a = slot_prf(recs)["amount"]
    assert (a["tp"], a["fp"], a["fn"], a["tn"]) == (1, 2, 2, 1)
    assert a["precision"] == 33.3 and a["recall"] == 33.3 and a["f1"] == 33.3
    assert a["accuracy"] == 40.0


def test_unknown_payment_counts_as_empty() -> None:
    from eval.metrics import slot_prf

    recs = [_rec({"payment_method": "cash"}, {"payment_method": "unknown"}),
            _rec({"payment_method": "card"}, {"payment_method": "card"})]
    p = slot_prf(recs)["payment_method"]
    assert (p["tp"], p["fp"], p["fn"]) == (1, 0, 1)
    assert p["precision"] == 100.0 and p["recall"] == 50.0 and p["f1"] == 66.7


def test_classification_report_and_confusion() -> None:
    from eval.metrics import classification_report

    rep = classification_report(["fuel", "fuel", "health", "transport"], ["fuel", "health", "health", "transport"])
    assert rep["accuracy"] == 75.0
    assert rep["per_class"]["fuel"] == {"precision": 100.0, "recall": 50.0, "f1": 66.7, "support": 2}
    assert rep["per_class"]["health"]["precision"] == 50.0
    assert rep["confusion"]["fuel"]["health"] == 1
    assert rep["macro"]["f1"] == round((66.7 + 66.7 + 100.0) / 3, 1)
