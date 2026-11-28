"""Relative/absolute dates and times against the fixed reference Friday 2026-11-20 14:00 (Cairo)."""
from __future__ import annotations

from datetime import date

import pytest

from voice_expense.dates import parse_datetime
from voice_expense.normalize import normalize_text, tokenize


def _dt(text: str, now):  # type: ignore[no-untyped-def]
    return parse_datetime(tokenize(normalize_text(text)), now)


def test_reference_is_friday(now) -> None:
    assert now.date() == date(2026, 11, 20) and now.weekday() == 4


@pytest.mark.parametrize("text,expected", [
    ("النهاردة", "2026-11-20"), ("النهارده", "2026-11-20"), ("اليوم", "2026-11-20"), ("today", "2026-11-20"),
    ("امبارح", "2026-11-19"), ("إمبارح", "2026-11-19"), ("أمس", "2026-11-19"), ("yesterday", "2026-11-19"),
    ("embare7", "2026-11-19"),
    ("أول امبارح", "2026-11-18"), ("اول امس", "2026-11-18"), ("the day before yesterday", "2026-11-18"),
    ("من يومين", "2026-11-18"), ("من ٣ أيام", "2026-11-17"), ("من تلات أيام", "2026-11-17"),
    ("3 days ago", "2026-11-17"), ("a week ago", "2026-11-13"),
    ("يوم السبت", "2026-11-14"), ("الحد", "2026-11-15"), ("يوم الاتنين", "2026-11-16"), ("التلات", "2026-11-17"),
    ("الأربعاء", "2026-11-18"), ("يوم الخميس اللي فات", "2026-11-19"), ("يوم الجمعة", "2026-11-20"),
    ("الجمعة اللي فاتت", "2026-11-13"), ("last Friday", "2026-11-13"), ("on Monday", "2026-11-16"),
    ("last Thursday", "2026-11-19"),
    ("5 نوفمبر", "2026-11-05"), ("٥ نوفمبر", "2026-11-05"), ("Nov 5", "2026-11-05"),
    ("5th of November", "2026-11-05"), ("٥/١١", "2026-11-05"), ("5/11", "2026-11-05"),
    ("5-11-2026", "2026-11-05"), ("2026-11-02", "2026-11-02"), ("12/11", "2026-11-12"),
    ("3 ديسمبر", "2025-12-03"),
])
def test_dates(text: str, expected: str, now) -> None:
    assert _dt(text, now).date.isoformat() == expected


def test_default_date_is_reference_date(now) -> None:
    r = _dt("دفعت 50 جنيه", now)
    assert r.date == now.date() and r.date_source == "default"


def test_weekday_never_in_future(now) -> None:
    for word in ("السبت", "الاحد", "الاتنين", "التلات", "الاربع", "الخميس", "الجمعه", "saturday", "sunday"):
        assert _dt(word, now).date <= now.date()


def test_tomorrow_is_flagged(now) -> None:
    r = _dt("بكرة", now)
    assert r.date == date(2026, 11, 21) and r.date_review


def test_last_week_is_vague(now) -> None:
    r = _dt("الأسبوع اللي فات", now)
    assert r.date == date(2026, 11, 13) and r.date_review and r.date_confidence < 0.6
    assert _dt("last week", now).date_review


@pytest.mark.parametrize("text,expected_time,review", [
    ("الصبح", "09:00", False), ("الضهر", "13:00", False), ("العصر", "16:00", False), ("بالليل", "21:00", False),
    ("this morning", "09:00", False), ("in the evening", "19:00", False),
    ("الساعة 7 بالليل", "19:00", False), ("الساعة ٣ العصر", "15:00", False), ("الساعة 10 الصبح", "10:00", False),
    ("الساعة تلاتة ونص العصر", "15:30", False), ("الساعة 12 بالليل", "00:00", False),
    ("at 7pm", "19:00", False), ("at 7:30 pm", "19:30", False), ("at 19:30", "19:30", False),
    ("الساعة 3", "03:00", True), ("at 7", "07:00", True),
])
def test_times(text: str, expected_time: str, review: bool, now) -> None:
    r = _dt(text, now)
    assert r.time == expected_time
    assert r.time_review is review


def test_yesterday_night(now) -> None:
    r = _dt("امبارح بالليل", now)
    assert r.date == date(2026, 11, 19) and r.time == "21:00"
    r = _dt("last night", now)
    assert r.date == date(2026, 11, 19) and r.time == "21:00"
