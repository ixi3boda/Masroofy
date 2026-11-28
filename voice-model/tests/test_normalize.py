"""Normalization of Arabic / English / mixed / Franco text."""
from __future__ import annotations

import pytest

from voice_expense.normalize import detect_language, fold, normalize_digits, normalize_text, prefix_variants, tokenize


def test_eastern_and_persian_digits() -> None:
    assert normalize_digits("٠١٢٣٤٥٦٧٨٩") == "0123456789"
    assert normalize_digits("۱۲۳") == "123"
    assert normalize_digits("١٢٫٥") == "12.5"
    assert normalize_digits("١٬٥٠٠") == "1500"


def test_diacritics_and_tatweel_removed() -> None:
    assert normalize_text("جُنَيْه") == "جنيه"
    assert normalize_text("بـ150") == "ب 150"


def test_alef_unified_and_ta_marbuta_kept() -> None:
    out = normalize_text("أوبر إمبارح آخر قهوة")
    assert out == "اوبر امبارح اخر قهوة"
    assert "ة" in out  # display text keeps ة


def test_alef_maqsura_at_word_end() -> None:
    assert normalize_text("على كشرى") == "علي كشري"


def test_fold_for_matching() -> None:
    assert fold("قهوة") == "قهوه"
    assert fold("دواء") == "دوا"
    assert fold("مائة") == "مايه"


@pytest.mark.parametrize("raw,expected", [
    ("150ج", "150 ج"),
    ("١٥٠ج.م", "150 ج.م"),
    ("150LE", "150 le"),
    ("150egp", "150 egp"),
    ("2.5k", "2.5 k"),
    ("5pm", "5 pm"),
    ("بـUber", "ب uber"),
])
def test_glued_tokens_split(raw: str, expected: str) -> None:
    assert normalize_text(raw) == expected


def test_franco_words_are_not_split() -> None:
    toks = [t.text for t in tokenize(normalize_text("dafa3t 150 f uber embare7"))]
    assert toks == ["dafa3t", "150", "f", "uber", "embare7"]


def test_latin_words_kept_in_mixed_text() -> None:
    toks = [t.text for t in tokenize(normalize_text("اشتريت من B.Tech و H&M"))]
    assert "b.tech" in toks and "h&m" in toks


def test_prefix_variants() -> None:
    rests = [r for _, r in prefix_variants("بالفيزا")]
    assert "فيزا" in rests
    rests = [r for _, r in prefix_variants("للدكتور")]
    assert "دكتور" in rests and "الدكتور" in rests
    assert [r for _, r in prefix_variants("فاوبر")][1] == "اوبر"


@pytest.mark.parametrize("text,lang", [
    ("دفعت 150 جنيه", "ar"),
    ("I paid 80 pounds", "en"),
    ("دفعت 150 جنيه في Uber", "mixed"),
    ("dafa3t 150 f uber", "en"),
])
def test_detect_language(text: str, lang: str) -> None:
    assert detect_language(text) == lang
