"""Merchant gazetteer: aliases in both scripts, ambiguity rules, fuzzy and pattern matching."""
from __future__ import annotations

import pytest

from voice_expense.merchants import get_gazetteer
from voice_expense.rule_extractor import extract_rules


def test_gazetteer_size() -> None:
    assert len(get_gazetteer()) >= 60


@pytest.mark.parametrize("text,merchant", [
    ("دفعت 150 في اوبر", "Uber"), ("دفعت 150 في أوبر", "Uber"), ("دفعت 150 في Uber", "Uber"),
    ("dafa3t 150 f uber", "Uber"), ("دفعت 150 فأوبر", "Uber"), ("دفعت بـUber 150", "Uber"),
    ("اشتريت من كارفور", "Carrefour"), ("from Carrefour", "Carrefour"),
    ("من بي تك", "B.Tech"), ("at B.Tech", "B.Tech"), ("men btech", "B.Tech"),
    ("في ستاربكس", "Starbucks"), ("كشري التحرير", "Koshary El Tahrir"), ("ابو طارق", "Abou Tarek"),
    ("من هايبر وان", "Hyper One"), ("at McDonald's", "McDonald's"), ("ماكدونالدز", "McDonald's"),
    ("صيدلية العزبي", "El Ezaby Pharmacy"), ("فودافون", "Vodafone"), ("نتفليكس", "Netflix"),
    ("ركبت المترو", "Cairo Metro"), ("من مترو ماركت", "Metro Market"), ("H&M", "H&M"),
])
def test_aliases(text: str, merchant: str, now) -> None:
    assert extract_rules(text, now).fields["merchant"] == merchant


@pytest.mark.parametrize("text", [
    "We paid the internet bill 450",      # "we" is a pronoun here
    "In total I paid 300 for lunch",      # "total" is a word here
    "paid 30 at noon for a sandwich",     # "noon" is a time here
    "اشتريت ايس كريم ب 20",               # "كريم" is cream, not Careem
    "عصير orange ب 15",                   # fruit, not the telecom company
])
def test_ambiguous_aliases_not_matched_without_context(text: str, now) -> None:
    assert extract_rules(text, now).fields["merchant"] is None


@pytest.mark.parametrize("text,merchant", [
    ("دفعت فاتورة النت لوي ٤٥٠", "WE"),
    ("Filled up gas at Total for 600 pounds", "TotalEnergies"),
    ("ordered from noon a phone case for 150", "Noon"),
    ("طلبت أكل من طلبات", "Talabat"),
    ("Recharged 50 pounds Orange credit", "Orange"),
])
def test_ambiguous_aliases_with_context(text: str, merchant: str, now) -> None:
    assert extract_rules(text, now).fields["merchant"] == merchant


def test_category_word_is_not_a_merchant(now) -> None:
    r = extract_rules("صرفت 250 على groceries", now)
    assert r.fields["merchant"] is None and r.fields["category"] == "groceries"


def test_fuzzy_match_typo(now) -> None:
    r = extract_rules("paid 90 at Starbuks", now)
    assert r.fields["merchant"] == "Starbucks"


def test_unknown_merchant_from_pattern_is_flagged(now) -> None:
    r = extract_rules("دفعت 20 جنيه في Route 66", now)
    assert r.fields["merchant"] == "Route 66"
    assert "merchant" in r.needs_review


def test_payment_wallet_is_not_merchant(now) -> None:
    r = extract_rules("حولت 500 جنيه فودافون كاش", now)
    assert r.fields["merchant"] is None and r.fields["payment_method"] == "wallet"


def test_canonical() -> None:
    g = get_gazetteer()
    assert g.canonical("أوبر") == "Uber"
    assert g.canonical("unknown shop") is None
