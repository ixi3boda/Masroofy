"""End-to-end rule extraction on the example utterances from the project brief."""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from voice_expense.rule_extractor import extract_rules

CASES = [
    ("دفعت 150 جنيه في Uber", {"amount": 150, "currency": "EGP", "merchant": "Uber", "category": "transport",
                               "date": date(2026, 11, 20)}),
    ("صرفت 250 على groceries امبارح", {"amount": 250, "merchant": None, "category": "groceries",
                                       "date": date(2026, 11, 19)}),
    ("I paid 80 pounds for coffee at Cilantro this morning", {"amount": 80, "merchant": "Cilantro",
                                                              "category": "food_dining", "time": "09:00"}),
    ("اشتريت شاحن من B.Tech بألف وخمسمية جنيه", {"amount": 1500, "merchant": "B.Tech", "category": "electronics",
                                                "note": "شاحن"}),
    ("دفعت ٣٠٠ كاش للدكتور يوم الخميس اللي فات", {"amount": 300, "payment_method": "cash", "category": "health",
                                                   "date": date(2026, 11, 19)}),
    ("dafa3t 150 f uber embare7", {"amount": 150, "merchant": "Uber", "date": date(2026, 11, 19)}),
    ("Paid 60 euros for a concert ticket on Nov 5", {"amount": 60, "currency": "EUR", "category": "entertainment",
                                                     "date": date(2026, 11, 5)}),
    ("اشتريت groceries من Breadfast ب 540 جنيه بالكارت", {"amount": 540, "payment_method": "card",
                                                          "merchant": "Breadfast"}),
    ("Paid rent 9000 pounds via InstaPay", {"payment_method": "wallet", "category": "housing"}),
]


@pytest.mark.parametrize("text,expected", CASES)
def test_examples(text: str, expected: dict, now) -> None:
    r = extract_rules(text, now)
    for k, v in expected.items():
        got = r.fields[k]
        if k == "amount":
            assert got == Decimal(v), (text, k, got)
        else:
            assert got == v, (text, k, got)


def test_language_and_normalized_text(now) -> None:
    r = extract_rules("دفعت ١٥٠ جنيه في Uber", now)
    assert r.language == "mixed"
    assert "150" in r.normalized_text


def test_empty_transcript_flags_everything(now) -> None:
    r = extract_rules("", now)
    assert r.fields["amount"] is None
    assert {"amount", "merchant", "category", "date"} <= set(r.needs_review)
    assert r.warnings


def test_confident_case_needs_no_review(now) -> None:
    r = extract_rules("دفعت 150 جنيه في اوبر امبارح", now)
    assert r.needs_review == []
    assert r.confidence["amount"] >= 0.9


def test_ambiguous_amount_flagged(now) -> None:
    r = extract_rules("coffee 45 and cake 30", now)
    assert "amount" in r.needs_review
