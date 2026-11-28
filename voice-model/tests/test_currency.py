"""Currency detection."""
from __future__ import annotations

import pytest

from voice_expense.currency import detect_currency
from voice_expense.normalize import normalize_text, tokenize


def _cur(text: str) -> tuple[str, float]:
    code, conf, _ = detect_currency(tokenize(normalize_text(text)))
    return code, conf


@pytest.mark.parametrize("text,code", [
    ("دفعت 150 جنيه", "EGP"),
    ("دفعت 150 جنية", "EGP"),
    ("150ج", "EGP"),
    ("١٥٠ج.م", "EGP"),
    ("150 ج م", "EGP"),
    ("150 L.E.", "EGP"),
    ("150LE", "EGP"),
    ("paid 150 pounds", "EGP"),
    ("sraft 200 geneh", "EGP"),
    ("100 دولار", "USD"),
    ("$50", "USD"),
    ("50 euros", "EUR"),
    ("20 €", "EUR"),
    ("100 ريال سعودي", "SAR"),
    ("200 درهم", "AED"),
    ("30 جنيه استرليني", "GBP"),
    ("40 pounds sterling", "GBP"),
    ("£25", "GBP"),
    ("دفعتها بالدولار 30", "USD"),
])
def test_currency_codes(text: str, code: str) -> None:
    assert _cur(text)[0] == code


def test_default_is_egp_with_lower_confidence() -> None:
    code, conf = _cur("صرفت 250 على groceries")
    assert code == "EGP"
    assert conf < 0.9


def test_single_letter_jeem_needs_a_number() -> None:
    # "ج" alone (not after a number) is just a letter.
    code, conf = _cur("حرف ج في الكلمة")
    assert conf < 0.9
