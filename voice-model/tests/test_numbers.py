"""Number parsing and amount selection."""
from __future__ import annotations

from decimal import Decimal

import pytest

from voice_expense.numbers import parse_digit_token, parse_number
from voice_expense.rule_extractor import extract_rules

EGYPTIAN = [
    ("واحد", 1), ("اتنين", 2), ("تلاتة", 3), ("خمستاشر", 15), ("حداشر", 11), ("تسعتاشر", 19),
    ("عشرين", 20), ("خمسة وعشرين", 25), ("مية", 100), ("ميتين", 200), ("تلتمية", 300), ("ربعمية", 400),
    ("خمسمية", 500), ("تمنمية", 800), ("ألف", 1000), ("ألفين", 2000), ("تلات تلاف", 3000),
    ("عشرة آلاف", 10000), ("ألف وخمسمية وخمسين", 1550), ("مية وخمسة وعشرين", 125), ("ألف ونص", 1500),
    ("مية ونص", 150), ("ألف وربع", 1250), ("ألف إلا ربع", 750), ("2 ألف", 2000), ("1.5 ألف", 1500),
    ("ثلاثمائة", 300), ("مائتين", 200), ("ثلاثة آلاف", 3000), ("مليون", 1_000_000), ("تمن تلاف", 8000),
]


@pytest.mark.parametrize("text,value", EGYPTIAN)
def test_arabic_number_words(text: str, value: int) -> None:
    assert parse_number(text) == Decimal(value)


ENGLISH_AND_DIGITS = [
    ("one hundred fifty", 150), ("two thousand five hundred", 2500), ("a hundred and twenty", 120),
    ("fifteen hundred", 1500), ("twenty-five", 25), ("ten and a half", Decimal("10.5")),
    ("2.5k", 2500), ("3k", 3000), ("1.2 million", 1_200_000), ("١٥٠", 150), ("۲۵۰", 250),
]


@pytest.mark.parametrize("text,value", ENGLISH_AND_DIGITS)
def test_english_words_and_digits(text: str, value: int) -> None:
    assert parse_number(text) == Decimal(value)


@pytest.mark.parametrize("token,value", [
    ("1,500", Decimal("1500")), ("1.500", Decimal("1500")), ("12.50", Decimal("12.50")),
    ("12,50", Decimal("12.50")), ("1,500.75", Decimal("1500.75")), ("0.500", Decimal("0.500")),
])
def test_digit_separators(token: str, value: Decimal) -> None:
    assert parse_digit_token(token) == value


@pytest.mark.parametrize("token", ["19:30", "5/11", "5-11-2026"])
def test_dates_and_times_are_not_numbers(token: str) -> None:
    assert parse_digit_token(token) is None


def _amount(text: str, now) -> Decimal | None:  # type: ignore[valid-type]
    return extract_rules(text, now).fields["amount"]


def test_time_vs_amount(now) -> None:
    r = extract_rules("الساعة ٨ الصبح دفعت ٤٠ جنيه قهوة", now)
    assert r.fields["amount"] == Decimal(40)
    assert r.fields["time"] == "08:00"


def test_quantity_vs_price(now) -> None:
    assert _amount("اشتريت 2 كيلو لحمة ب 900 جنيه", now) == Decimal(900)
    assert _amount("Bought 2 kg of chicken for 380 pounds", now) == Decimal(380)


def test_date_number_is_not_amount(now) -> None:
    assert _amount("اشتريت تذكرة سينما ب ٢٢٠ جنيه يوم ٥ نوفمبر", now) == Decimal(220)


def test_merchant_number_is_not_amount(now) -> None:
    r = extract_rules("اشتريت medicine من 19011 ب 210 جنيه", now)
    assert r.fields["amount"] == Decimal(210)
    assert r.fields["merchant"] == "19011 Pharmacy"


def test_price_word_is_not_eight(now) -> None:
    r = extract_rules("دفعت تمن البنزين امبارح", now)
    assert r.fields["amount"] is None
    assert "amount" in r.needs_review


def test_half_pound_after_currency(now) -> None:
    assert _amount("عشرة جنيه ونص عيش", now) == Decimal("10.5")
    assert _amount("دفعت عشرة جنيه وخمسين قرش مواصلات", now) == Decimal("10.5")


def test_glued_prefix_number(now) -> None:
    assert _amount("اشتريت بـ150 جنيه", now) == Decimal(150)
    assert _amount("اشتريت شاحن بألف وخمسمية", now) == Decimal(1500)
