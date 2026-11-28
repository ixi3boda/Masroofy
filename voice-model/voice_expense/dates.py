"""Relative and absolute date/time parsing (Arabic, English, Franco).

WHY explicit `now`:
    "امبارح" means a different day every day. Every function takes the
    reference time `now` (Africa/Cairo) so tests and evaluation always give
    the same answer. Nothing here ever reads the system clock.

Conventions (also in docs/DECISIONS.md):
    * Weekday names mean the most recent occurrence that is not in the future
      ("يوم الخميس" on a Friday = yesterday). With "اللي فات"/"الماضي"/"last",
      the same weekday as today means 7 days ago.
    * "5/11" is day/month (Egyptian convention).
    * A day+month without a year that would be in the future is moved to the
      previous year (expenses are in the past).
    * Default times for time-of-day words: الصبح/morning 09:00, الضهر/noon
      13:00, العصر/afternoon 16:00, المغرب 18:00, المسا/evening 19:00,
      بالليل/night 21:00.
    * "الساعة 3" without بالليل/العصر/am/pm keeps 03:00 but asks the user to
      review the time.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Optional

from .normalize import Token, prefix_variants

# --- vocab (folded keys) ------------------------------------------------------
TODAY_WORDS = {"النهارده", "انهارده", "النهاردا", "اليوم", "today", "tonight", "ennaharda", "elnaharda",
               "nharda", "innaharda", "naharda", "enaharda"}
YESTERDAY_WORDS = {"امبارح", "مبارح", "امس", "البارحه", "yesterday", "embare7", "mbare7", "embareh",
                   "imbarih", "mbarh", "embar7", "imbare7"}
TOMORROW_WORDS = {"بكره", "بكرا", "tomorrow", "bokra", "bukra"}
LAST_WORDS_AFTER = [("اللي", "فات"), ("الي", "فات"), ("اللي", "فاتت"), ("الماضي",), ("الفايت",), ("اللي", "فاته"),
                    ("elly", "fat"), ("eli", "fat"), ("ely", "fat")]
NEXT_WORDS_AFTER = [("اللي", "جاي"), ("الجاي",), ("القادم",)]

TIME_OF_DAY: dict[str, str] = {
    "الصبح": "09:00", "صباحا": "09:00", "الصباح": "09:00", "صبح": "09:00", "morning": "09:00",
    "sob7": "09:00", "elsob7": "09:00",
    "الضهر": "13:00", "الظهر": "13:00", "ضهرا": "13:00", "ظهرا": "13:00", "الضهريه": "13:00",
    "dohr": "13:00", "eldohr": "13:00", "lunchtime": "13:00", "midday": "13:00",
    "العصر": "16:00", "عصر": "16:00", "afternoon": "16:00", "3asr": "16:00", "el3asr": "16:00",
    "المغرب": "18:00", "maghrib": "18:00", "sunset": "18:00",
    "المسا": "19:00", "مساء": "19:00", "evening": "19:00", "masa": "19:00", "elmasa": "19:00",
    "بالليل": "21:00", "الليل": "21:00", "ليلا": "21:00", "بليل": "21:00", "ليل": "21:00",
    "night": "21:00", "tonight": "21:00", "bellel": "21:00", "belleil": "21:00", "bel-leil": "21:00", "leil": "21:00",
}
# Words that, after an hour, mean PM / AM.
PM_WORDS = {"بالليل", "الليل", "بليل", "ليلا", "مساء", "المسا", "م", "pm", "p.m", "evening", "night",
            "العصر", "المغرب", "bellel", "belleil", "leil"}
NIGHT_WORDS = {"بالليل", "الليل", "بليل", "ليلا", "night", "bellel", "belleil", "leil"}
AM_WORDS = {"الصبح", "صباحا", "الصباح", "ص", "am", "a.m", "morning", "sob7", "elsob7"}
NOON_WORDS = {"الضهر", "الظهر", "ضهرا", "ظهرا", "dohr", "eldohr", "noon", "afternoon"}
HOUR_PREFIX = {"الساعه", "ساعه", "sa3a", "elsa3a"}
EN_TIME_PREPS = {"at", "around", "by", "about"}

WEEKDAYS: dict[str, int] = {
    "السبت": 5, "الاحد": 6, "الحد": 6, "الاتنين": 0, "الاثنين": 0, "التلات": 1, "الثلاثا": 1,
    "التلاتا": 1, "الثلاث": 1, "الاربع": 2, "الاربعا": 2, "الخميس": 3, "الجمعه": 4,
    "monday": 0, "tuesday": 1, "wednesday": 2, "thursday": 3, "friday": 4, "saturday": 5, "sunday": 6,
    "mon": 0, "tue": 1, "tues": 1, "wed": 2, "thu": 3, "thurs": 3, "fri": 4, "sat": 5,
    "sabt": 5, "elsabt": 5, "7ad": 6, "el7ad": 6, "khamis": 3, "elkhamis": 3, "gom3a": 4, "elgom3a": 4,
}
MONTHS: dict[str, int] = {
    "يناير": 1, "فبراير": 2, "مارس": 3, "ابريل": 4, "مايو": 5, "يونيو": 6, "يوليو": 7, "اغسطس": 8,
    "سبتمبر": 9, "اكتوبر": 10, "نوفمبر": 11, "ديسمبر": 12,
    "january": 1, "february": 2, "march": 3, "april": 4, "may": 5, "june": 6, "july": 7, "august": 8,
    "september": 9, "october": 10, "november": 11, "december": 12,
    "jan": 1, "feb": 2, "mar": 3, "apr": 4, "jun": 6, "jul": 7, "aug": 8, "sep": 9, "sept": 9,
    "oct": 10, "nov": 11, "dec": 12,
}
# "may"/"mar" are also normal words, so they only count next to a number.
_MONTH_NEEDS_NUMBER = {"may", "mar", "jun", "dec", "sat", "sun", "wed"}
DAY_UNITS = {"يوم": 1, "ايام": 1, "يومين": 2, "day": 1, "days": 1, "ayam": 1,
             "اسبوع": 7, "اسابيع": 7, "اسبوعين": 14, "week": 7, "weeks": 7}
_ORDINAL_RE = re.compile(r"^(\d{1,2})(st|nd|rd|th)$")
_DMY_RE = re.compile(r"^(\d{1,2})[/\-.](\d{1,2})(?:[/\-.](\d{2,4}))?$")
_YMD_RE = re.compile(r"^(\d{4})[/\-.](\d{1,2})[/\-.](\d{1,2})$")
_HM_RE = re.compile(r"^(\d{1,2}):(\d{2})$")


@dataclass
class DateTimeResult:
    """Parsed date and time with confidences and the tokens that were used."""

    date: date
    time: Optional[str] = None
    date_confidence: float = 0.7
    time_confidence: float = 0.0
    date_review: bool = False
    time_review: bool = False
    date_source: str = "default"
    consumed: set[int] = field(default_factory=set)
    month_indices: set[int] = field(default_factory=set)
    notes: list[str] = field(default_factory=list)


@dataclass
class _Cand:
    value: date
    conf: float
    review: bool
    source: str
    priority: int


def _variants(tok: Token) -> list[str]:
    return [rest for _, rest in prefix_variants(tok.fold)]


def _match_any(tok: Token, vocab: set[str] | dict) -> Optional[str]:
    for v in _variants(tok):
        if v in vocab:
            return v
    return None


def _seq_at(tokens: list[Token], i: int, seq: tuple[str, ...]) -> bool:
    if i + len(seq) > len(tokens):
        return False
    return all(tokens[i + k].fold == seq[k] for k in range(len(seq)))


def _number_at(tokens: list[Token], i: int) -> Optional[tuple[float, int]]:
    """Parse a small number (digits or words) at tokens[i]; returns (value, end)."""
    from .numbers import _parse_at  # local import: numbers imports nothing from here

    if i >= len(tokens):
        return None
    m = _ORDINAL_RE.match(tokens[i].fold)
    if m:
        return float(m.group(1)), i + 1
    sp = _parse_at(tokens, i, set())
    if sp is None or sp.end == i:
        return None
    return float(sp.value), sp.end


def _safe_date(y: int, m: int, d: int) -> Optional[date]:
    try:
        return date(y, m, d)
    except ValueError:
        return None


def _past_or_previous_year(today: date, month: int, day: int) -> Optional[date]:
    d = _safe_date(today.year, month, day)
    if d is None:
        return None
    if d > today:
        d2 = _safe_date(today.year - 1, month, day)
        return d2
    return d


def _fmt(h: int, m: int) -> str:
    return f"{h % 24:02d}:{m:02d}"


def parse_datetime(tokens: list[Token], now: datetime, skip: Optional[set[int]] = None) -> DateTimeResult:
    """Find date and time expressions in `tokens`, relative to `now` (aware, Cairo)."""
    skip = skip or set()
    today = now.date()
    cands: list[_Cand] = []
    consumed: set[int] = set()
    month_idx: set[int] = set()
    notes: list[str] = []
    time_value: Optional[str] = None
    time_conf = 0.0
    time_review = False
    time_explicit = False
    n = len(tokens)

    def is_last_after(j: int) -> int:
        for seq in LAST_WORDS_AFTER:
            if _seq_at(tokens, j, seq):
                return len(seq)
        return 0

    def is_next_after(j: int) -> int:
        for seq in NEXT_WORDS_AFTER:
            if _seq_at(tokens, j, seq):
                return len(seq)
        return 0

    i = 0
    while i < n:
        if i in skip:
            i += 1
            continue
        tok = tokens[i]
        f = tok.fold

        # ---- "اول امبارح" / "day before yesterday" -------------------------------
        if f in ("اول", "awel", "awal") and i + 1 < n and _match_any(tokens[i + 1], YESTERDAY_WORDS):
            cands.append(_Cand(today - timedelta(days=2), 0.9, False, "relative", 3))
            consumed.update({i, i + 1})
            i += 2
            continue
        if _seq_at(tokens, i, ("day", "before", "yesterday")) or _seq_at(tokens, i, ("the", "day", "before", "yesterday")):
            L = 3 if f == "day" else 4
            cands.append(_Cand(today - timedelta(days=2), 0.9, False, "relative", 3))
            consumed.update(range(i, i + L))
            i += L
            continue
        # ---- "بعد بكره" ---------------------------------------------------------
        if f == "بعد" and i + 1 < n and _match_any(tokens[i + 1], TOMORROW_WORDS):
            cands.append(_Cand(today + timedelta(days=2), 0.5, True, "future", 3))
            consumed.update({i, i + 1})
            notes.append("future date")
            i += 2
            continue
        # ---- "last night" / "this morning" ---------------------------------------
        if f == "last" and i + 1 < n and tokens[i + 1].fold == "night":
            cands.append(_Cand(today - timedelta(days=1), 0.85, False, "relative", 3))
            if not time_explicit:
                time_value, time_conf = "21:00", 0.6
            consumed.update({i, i + 1})
            i += 2
            continue
        if f == "this" and i + 1 < n and tokens[i + 1].fold in ("morning", "afternoon", "evening"):
            cands.append(_Cand(today, 0.9, False, "relative", 2))
            if not time_explicit:
                time_value, time_conf = TIME_OF_DAY[tokens[i + 1].fold], 0.6
            consumed.update({i, i + 1})
            i += 2
            continue
        # ---- "last week" / "الاسبوع اللي فات" / "last month" ---------------------
        if f == "last" and i + 1 < n and tokens[i + 1].fold in ("week", "month"):
            days = 7 if tokens[i + 1].fold == "week" else 30
            cands.append(_Cand(today - timedelta(days=days), 0.4, True, "vague", 2))
            consumed.update({i, i + 1})
            i += 2
            continue
        if _match_any(tok, {"الاسبوع", "الشهر", "اسبوع"}) is not None and i + 1 < n:
            L = is_last_after(i + 1)
            if L:
                days = 7 if "سبوع" in f else 30
                cands.append(_Cand(today - timedelta(days=days), 0.4, True, "vague", 2))
                consumed.update(range(i, i + 1 + L))
                i += 1 + L
                continue
        # ---- weekdays -------------------------------------------------------------
        wd_key = _match_any(tok, WEEKDAYS)
        if wd_key is not None and not (wd_key in _MONTH_NEEDS_NUMBER):
            start = i
            if i > 0 and tokens[i - 1].fold in ("يوم", "on", "el", "youm", "yom") and (i - 1) not in skip:
                start = i - 1
            strict = False
            end = i + 1
            if i > 0 and tokens[i - 1].fold == "last":
                strict = True
                start = i - 1
            L = is_last_after(i + 1)
            if L:
                strict = True
                end = i + 1 + L
            Ln = is_next_after(i + 1)
            target = WEEKDAYS[wd_key]
            delta = (today.weekday() - target) % 7
            if strict and delta == 0:
                delta = 7
            if Ln:
                fwd = (target - today.weekday()) % 7 or 7
                cands.append(_Cand(today + timedelta(days=fwd), 0.5, True, "future", 3))
                end = i + 1 + Ln
                notes.append("future weekday")
            else:
                cands.append(_Cand(today - timedelta(days=delta), 0.8, False, "weekday", 3))
            consumed.update(range(start, end))
            i = end
            continue
        # ---- "من يومين" / "من 3 ايام" / "3 days ago" / "a week ago" ---------------
        if f in ("من", "min", "men", "mn") and i + 1 < n:
            nxt = tokens[i + 1].fold
            if nxt in ("يومين", "اسبوعين", "اسبوع", "يوم", "شهر"):
                days = {"يومين": 2, "اسبوعين": 14, "اسبوع": 7, "يوم": 1, "شهر": 30}[nxt]
                vague = nxt in ("اسبوع", "اسبوعين", "شهر")
                cands.append(_Cand(today - timedelta(days=days), 0.5 if vague else 0.85, vague, "relative", 3))
                consumed.update({i, i + 1})
                i += 2
                continue
            num = _number_at(tokens, i + 1)
            if num and num[1] < n and tokens[num[1]].fold in DAY_UNITS and num[0] <= 60:
                unit = DAY_UNITS[tokens[num[1]].fold]
                days = int(num[0]) * unit
                cands.append(_Cand(today - timedelta(days=days), 0.85 if unit == 1 else 0.5, unit != 1, "relative", 3))
                consumed.update(range(i, num[1] + 1))
                i = num[1] + 1
                continue
        num = None
        if tok.is_number or f in ("a", "an") or (tok.fold and not tok.is_arabic):
            if f in ("a", "an"):
                num = (1.0, i + 1)
            else:
                num = _number_at(tokens, i)
            if num and num[1] + 1 < n and tokens[num[1]].fold in DAY_UNITS and tokens[num[1] + 1].fold == "ago":
                unit = DAY_UNITS[tokens[num[1]].fold]
                days = int(num[0]) * unit
                cands.append(_Cand(today - timedelta(days=days), 0.85 if unit == 1 else 0.5, unit != 1, "relative", 3))
                consumed.update(range(i, num[1] + 2))
                i = num[1] + 2
                continue
        # ---- explicit numeric dates: 5/11, 5-11-2026, 2026-11-05 -------------------
        if tok.is_number:
            m = _YMD_RE.match(tok.text)
            if m:
                d = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
                if d:
                    cands.append(_Cand(d, 0.95, d > today, "explicit", 4))
                    consumed.add(i)
                    i += 1
                    continue
            m = _DMY_RE.match(tok.text)
            if m and ("/" in tok.text or "-" in tok.text):
                day_v, mon_v = int(m.group(1)), int(m.group(2))
                if m.group(3):
                    yr = int(m.group(3))
                    yr = yr + 2000 if yr < 100 else yr
                    d = _safe_date(yr, mon_v, day_v)
                    if d:
                        cands.append(_Cand(d, 0.95, d > today, "explicit", 4))
                        consumed.add(i)
                        i += 1
                        continue
                else:
                    d = _past_or_previous_year(today, mon_v, day_v)
                    if d:
                        cands.append(_Cand(d, 0.85, False, "explicit", 4))
                        consumed.add(i)
                        i += 1
                        continue
        # ---- "5 نوفمبر", "5th of November", "Nov 5", "نوفمبر 5" --------------------
        month_key = _match_any(tok, MONTHS)
        if month_key is not None:
            # number after the month: "Nov 5", "November 5th"
            j = i + 1
            if j < n and tokens[j].fold == ".":
                j += 1
            num = _number_at(tokens, j) if j < n else None
            before = None
            k = i - 1
            if k >= 0 and tokens[k].fold in ("of",):
                k -= 1
            if k >= 0 and (k not in skip):
                before = _number_at(tokens, k)
                if before and before[1] not in (i, i - 1 if tokens[i - 1].fold == "of" else -99):
                    before = None
            day_num: Optional[int] = None
            used = {i}
            if before and 1 <= before[0] <= 31 and before[0] == int(before[0]):
                day_num = int(before[0])
                used.update(range(k, i))
            elif num and 1 <= num[0] <= 31 and num[0] == int(num[0]):
                day_num = int(num[0])
                used.update(range(j, num[1]))
            if day_num is None:
                if month_key in _MONTH_NEEDS_NUMBER:
                    i += 1
                    continue
                # month alone ("في نوفمبر") -> first day of that month, vague
                d = _past_or_previous_year(today, MONTHS[month_key], 1)
                if d:
                    cands.append(_Cand(d, 0.3, True, "vague", 1))
                    consumed.add(i)
                    month_idx.add(i)
                i += 1
                continue
            # optional year after
            last = max(used)
            year: Optional[int] = None
            if last + 1 < n and tokens[last + 1].is_number and re.fullmatch(r"\d{4}", tokens[last + 1].text):
                year = int(tokens[last + 1].text)
                used.add(last + 1)
            if year:
                d = _safe_date(year, MONTHS[month_key], day_num)
                review = bool(d and d > today)
            else:
                d = _past_or_previous_year(today, MONTHS[month_key], day_num)
                review = False
            if d:
                cands.append(_Cand(d, 0.9, review, "explicit", 4))
                consumed.update(used)
                month_idx.add(i)
            i = max(used) + 1
            continue
        # ---- "يوم 15" / "on the 15th" ---------------------------------------------
        if f in ("يوم",) and i + 1 < n and tokens[i + 1].is_number:
            num = _number_at(tokens, i + 1)
            nxt_f = tokens[num[1]].fold if num and num[1] < n else ""
            if num and 1 <= num[0] <= 31 and nxt_f not in ("جنيه", "ج") and num[0] == int(num[0]):
                day_num = int(num[0])
                d = _safe_date(today.year, today.month, day_num)
                if d is None or d > today:
                    prev_month = (today.replace(day=1) - timedelta(days=1))
                    d = _safe_date(prev_month.year, prev_month.month, day_num)
                if d:
                    cands.append(_Cand(d, 0.7, False, "explicit", 4))
                    consumed.update(range(i, num[1]))
                    i = num[1]
                    continue
        if f == "the" and i + 1 < n and _ORDINAL_RE.match(tokens[i + 1].fold):
            day_num = int(_ORDINAL_RE.match(tokens[i + 1].fold).group(1))  # type: ignore[union-attr]
            d = _safe_date(today.year, today.month, day_num)
            if d is None or d > today:
                prev_month = (today.replace(day=1) - timedelta(days=1))
                d = _safe_date(prev_month.year, prev_month.month, day_num)
            if d:
                cands.append(_Cand(d, 0.7, False, "explicit", 4))
                consumed.update({i, i + 1})
                if i > 0 and tokens[i - 1].fold == "on":
                    consumed.add(i - 1)
                i += 2
                continue

        # ---- explicit times ---------------------------------------------------------
        hour_hit = None  # (hour_float, minute, end_index, start_index)
        if _match_any(tok, HOUR_PREFIX) is not None and i + 1 < n:
            hm = _HM_RE.match(tokens[i + 1].text)
            if hm:
                hour_hit = (int(hm.group(1)), int(hm.group(2)), i + 2, i)
            else:
                num = _number_at(tokens, i + 1)
                if num and 0 <= num[0] <= 24:
                    hv = num[0]
                    hour_hit = (int(hv), int(round((hv - int(hv)) * 60)), num[1], i)
        elif tok.is_number and _HM_RE.match(tok.text):
            hm = _HM_RE.match(tok.text)
            assert hm is not None
            start_i = i - 1 if i > 0 and tokens[i - 1].fold in EN_TIME_PREPS else i
            hour_hit = (int(hm.group(1)), int(hm.group(2)), i + 1, start_i)
        elif f in EN_TIME_PREPS and i + 1 < n:
            num = _number_at(tokens, i + 1)
            nxt = tokens[num[1]].fold if num and num[1] < n else ""
            money_words = {"جنيه", "pounds", "pound", "egp", "le", "$", "dollars", "usd", "euros", "eur"}
            if num and 0 < num[0] <= 24 and num[0] == int(num[0]) and nxt not in money_words:
                hour_hit = (int(num[0]), 0, num[1], i)
            elif tokens[i + 1].fold == "noon":
                if not time_explicit:
                    time_value, time_conf = "13:00", 0.6
                consumed.update({i, i + 1})
                i += 2
                continue
        elif tok.is_number and i + 1 < n and tokens[i + 1].fold in ("pm", "am", "p.m", "a.m", "o'clock", "oclock"):
            num = _number_at(tokens, i)
            if num and 0 < num[0] <= 12:
                hour_hit = (int(num[0]), int(round((num[0] - int(num[0])) * 60)), num[1], i)
        if hour_hit is not None:
            h, mi, end, start_i = hour_hit
            qual_used = 0
            review = True
            if end < n:
                qf = tokens[end].fold
                qv = [v for v in _variants(tokens[end])]
                if qf in ("pm", "p.m") or any(v in PM_WORDS for v in qv):
                    if h < 12:
                        h += 12
                    elif h == 12 and qf not in ("pm", "p.m") and any(v in NIGHT_WORDS for v in qv):
                        h = 0  # "الساعة 12 بالليل" = midnight
                    review = False
                    qual_used = 1
                elif qf in ("am", "a.m") or any(v in AM_WORDS for v in qv):
                    if h == 12:
                        h = 0
                    review = False
                    qual_used = 1
                elif any(v in NOON_WORDS for v in qv):
                    if 1 <= h <= 5:
                        h += 12
                    review = False
                    qual_used = 1
                elif qf in ("o'clock", "oclock"):
                    qual_used = 1
                    if end + 1 < n:
                        nf = tokens[end + 1].fold
                        if nf in ("pm",) or nf in PM_WORDS:
                            h = h + 12 if h < 12 else h
                            review = False
                            qual_used = 2
                        elif nf in AM_WORDS:
                            review = False
                            qual_used = 2
                elif qf == "in" and end + 2 < n and tokens[end + 1].fold == "the":
                    q2 = tokens[end + 2].fold
                    if q2 in ("evening", "afternoon", "night"):
                        h = h + 12 if h < 12 else h
                        review, qual_used = False, 3
                    elif q2 == "morning":
                        review, qual_used = False, 3
                elif qf == "at" and end + 1 < n and tokens[end + 1].fold == "night":
                    h = h + 12 if h < 12 else h
                    review, qual_used = False, 2
            if h > 12:
                review = False
            if 0 <= h <= 23 and 0 <= mi <= 59:
                time_value = _fmt(h, mi)
                time_conf = 0.55 if review else 0.9
                time_review = review
                time_explicit = True
                consumed.update(range(start_i, end + qual_used))
                i = end + qual_used
                continue
        # ---- today / yesterday / tomorrow --------------------------------------------
        if _match_any(tok, YESTERDAY_WORDS) is not None:
            cands.append(_Cand(today - timedelta(days=1), 0.95, False, "relative", 3))
            consumed.add(i)
            i += 1
            continue
        if _match_any(tok, TOMORROW_WORDS) is not None:
            cands.append(_Cand(today + timedelta(days=1), 0.5, True, "future", 3))
            consumed.add(i)
            notes.append("future date (tomorrow)")
            i += 1
            continue
        if _match_any(tok, TODAY_WORDS) is not None:
            cands.append(_Cand(today, 0.95, False, "relative", 2))
            consumed.add(i)
            if f == "tonight" and not time_explicit:
                time_value, time_conf = "21:00", 0.6
            i += 1
            continue
        # ---- time-of-day words ----------------------------------------------------------
        tod = _match_any(tok, TIME_OF_DAY)
        if tod is not None:
            prev_f = tokens[i - 1].fold if i > 0 else ""
            # English "night"/"evening" after a number is a duration ("2 nights")
            if not (tok.is_latin and i > 0 and tokens[i - 1].is_number):
                if not time_explicit:
                    time_value, time_conf = TIME_OF_DAY[tod], 0.6
                consumed.add(i)
                if prev_f in ("in", "at", "this", "the") and (i - 1) not in skip:
                    consumed.add(i - 1)
                    if prev_f == "the" and i > 1 and tokens[i - 2].fold == "in":
                        consumed.add(i - 2)
            i += 1
            continue
        if f == "noon" and i > 0 and tokens[i - 1].fold in EN_TIME_PREPS | {"this"} and not time_explicit:
            time_value, time_conf = "13:00", 0.6
            consumed.update({i - 1, i})
            i += 1
            continue
        i += 1

    # ---- choose the date -----------------------------------------------------------------
    if cands:
        cands.sort(key=lambda c: (-c.priority, -c.conf))
        best = cands[0]
        distinct = {c.value for c in cands}
        result = DateTimeResult(
            date=best.value,
            date_confidence=best.conf,
            date_review=best.review,
            date_source=best.source,
        )
        if len(distinct) > 1:
            # e.g. "امبارح" + "يوم 5": keep the most specific one but ask the user.
            result.date_confidence = min(best.conf, 0.5)
            result.date_review = True
            notes.append("several different dates mentioned")
    else:
        result = DateTimeResult(date=today, date_confidence=0.7, date_source="default")
    result.time = time_value
    result.time_confidence = time_conf
    result.time_review = time_review
    result.consumed = consumed
    result.month_indices = month_idx
    result.notes = notes
    return result
