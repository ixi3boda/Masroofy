"""Category keywords and precedence: explicit keyword > merchant default > LLM > other."""
from __future__ import annotations

import pytest

from voice_expense.categories import category_ids, classify, load_categories
from voice_expense.normalize import normalize_text, tokenize
from voice_expense.rule_extractor import extract_rules


def test_all_required_categories_present() -> None:
    expected = {"food_dining", "groceries", "transport", "fuel", "shopping", "electronics", "bills_utilities",
                "mobile_internet", "health", "education", "entertainment", "subscriptions", "housing",
                "personal_care", "gifts_donations", "travel", "income", "other"}
    assert set(category_ids()) == expected


def test_each_category_has_15_keywords() -> None:
    for c in load_categories():
        assert len(c.keywords) >= 15, c.id


def test_keyword_beats_merchant_default(now) -> None:
    r = extract_rules("دفعت 500 في كارفور على هدوم", now)
    assert r.fields["merchant"] == "Carrefour"
    assert r.fields["category"] == "shopping"
    assert [c["category"] for c in r.category_candidates][:2] == ["shopping", "groceries"]


def test_merchant_default_used_without_keyword(now) -> None:
    r = extract_rules("دفعت 150 جنيه في اوبر", now)
    assert r.fields["category"] == "transport"
    assert r.confidence["category"] < 0.85


def test_llm_category_beats_other_only() -> None:
    toks = tokenize(normalize_text("دفعت 100 جنيه"))
    res = classify(toks, llm_category="travel")
    assert res.category == "travel" and res.source == "llm"
    res2 = classify(tokenize(normalize_text("دفعت 100 جنيه بنزين")), llm_category="travel")
    assert res2.category == "fuel"


def test_fallback_other_low_confidence(now) -> None:
    r = extract_rules("دفعت 100 جنيه", now)
    assert r.fields["category"] == "other"
    assert "category" in r.needs_review


@pytest.mark.parametrize("text,cat", [
    ("ركبت تاكسي", "transport"), ("دفعت للدكتور", "health"), ("coffee", "food_dining"),
    ("فاتورة النت", "mobile_internet"), ("فاتورة الكهربا", "bills_utilities"), ("شاحن", "electronics"),
    ("ايجار الشقة", "housing"), ("كورس انجليزي", "education"), ("haircut", "personal_care"),
    ("تبرع", "gifts_donations"), ("hotel", "travel"), ("benzine", "fuel"), ("سينما", "entertainment"),
    ("اشتراك", "subscriptions"), ("خضار", "groceries"), ("هدوم", "shopping"),
])
def test_keywords(text: str, cat: str) -> None:
    assert classify(tokenize(normalize_text(text))).category == cat


def test_income_category_from_transaction_type(now) -> None:
    r = extract_rules("قبضت المرتب 12000 جنيه", now)
    assert r.fields["transaction_type"] == "income" and r.fields["category"] == "income"


def test_paying_a_salary_is_an_expense(now) -> None:
    r = extract_rules("دفعت مرتب البواب 1500 جنيه", now)
    assert r.fields["transaction_type"] == "expense"
