"""Numbers: digits, English words, Egyptian/MSA Arabic words, and picking the money amount.

WHY this is the hardest part of the rules:
    People say amounts in many ways: "150", "1,500", "2.5k", "ألف وخمسمية",
    "مية ونص", "fifteen hundred", "2 ألف". A sentence can also contain other
    numbers that are NOT money: "الساعة 3", "2 كيلو", "5 نوفمبر", "7 Up".
    This module (1) finds every number span in the token list and (2) scores
    each span to choose the one that is most likely the amount.

Thousands/decimal rule (documented in docs/DECISIONS.md):
    "1,500" and "1.500" are both 1500 (a separator followed by exactly three
    digits is a thousands separator). "12.50" and "12,50" are decimals.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Iterable, Optional

from .normalize import Token, fold

D = Decimal

# ---------------------------------------------------------------------------
# Word tables (keys are FOLDED: ة->ه, ى->ي, alef unified, ؤ->و, ئ->ي, final ء dropped)
# ---------------------------------------------------------------------------
UNITS: dict[str, int] = {
    # Arabic (Egyptian + MSA)
    "واحد": 1, "واحده": 1, "وحده": 1, "اتنين": 2, "اثنين": 2, "اثنان": 2, "اتنان": 2,
    "تلاته": 3, "ثلاثه": 3, "تلات": 3, "ثلاث": 3, "اربعه": 4, "اربع": 4, "خمسه": 5, "خمس": 5,
    "سته": 6, "ست": 6, "سبعه": 7, "سبع": 7, "تمانيه": 8, "ثمانيه": 8, "تمان": 8, "ثمان": 8,
    "ثماني": 8, "تسعه": 9, "تسع": 9, "عشره": 10, "عشر": 10,
    "احد": 1, "احدي": 1, "اثنا": 2, "اثني": 2,
    # English
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18, "nineteen": 19,
    # Franco-Arabic
    "wa7ed": 1, "etnen": 2, "itnein": 2, "talata": 3, "arba3a": 4, "khamsa": 5, "5amsa": 5,
    "setta": 6, "sab3a": 7, "tamanya": 8, "tes3a": 9, "3ashra": 10, "3ashara": 10,
}
TEENS: dict[str, int] = {
    "حداشر": 11, "احداشر": 11, "حادشر": 11, "اتناشر": 12, "اطناشر": 12, "اتنشر": 12,
    "تلتاشر": 13, "تلاتاشر": 13, "ثلاتاشر": 13, "تلطاشر": 13, "اربعتاشر": 14, "اربعطاشر": 14,
    "خمستاشر": 15, "خمسطاشر": 15, "ستاشر": 16, "سطاشر": 16, "سبعتاشر": 17, "سبعطاشر": 17,
    "تمنتاشر": 18, "تمانتاشر": 18, "تمنطاشر": 18, "تسعتاشر": 19, "تسعطاشر": 19,
    "7edashar": 11, "etnashar": 12, "talatashar": 13, "arba3tashar": 14, "khamastashar": 15,
}
TENS: dict[str, int] = {
    "عشرين": 20, "عشرون": 20, "تلاتين": 30, "ثلاثين": 30, "ثلاثون": 30, "اربعين": 40, "اربعون": 40,
    "خمسين": 50, "خمسون": 50, "ستين": 60, "ستون": 60, "سبعين": 70, "سبعون": 70,
    "تمانين": 80, "ثمانين": 80, "ثمانون": 80, "تسعين": 90, "تسعون": 90,
    "twenty": 20, "thirty": 30, "forty": 40, "fourty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
    "3eshrin": 20, "3eshreen": 20, "talatin": 30, "talateen": 30, "arbe3in": 40, "khamsin": 50,
    "khamseen": 50, "5amsin": 50, "settin": 60, "sab3in": 70, "tamanin": 80, "tes3in": 90,
}
# Words meaning "hundred" that multiply what came before ("تلات مية" = 300).
HUNDRED_MULT: dict[str, int] = {
    "ميه": 100, "مايه": 100, "مئه": 100, "ميت": 100, "hundred": 100, "hundreds": 100,
    "meya": 100, "mya": 100, "mia": 100, "miya": 100, "meet": 100,
}
# Fixed hundreds ("خمسمية" = 500).
HUNDRED_FIXED: dict[str, int] = {
    "ميتين": 200, "مئتين": 200, "مئتان": 200, "ميتان": 200, "مايتين": 200, "متين": 200,
    "تلتميه": 300, "تلاتميه": 300, "ثلاثمايه": 300, "ثلثمايه": 300, "ثلاتمايه": 300, "تلتمايه": 300,
    "ربعميه": 400, "اربعميه": 400, "اربعمايه": 400, "ربعمايه": 400,
    "خمسميه": 500, "خمسمايه": 500, "ستميه": 600, "ستمايه": 600, "سبعميه": 700, "سبعمايه": 700,
    "تمنميه": 800, "تمانميه": 800, "ثمانمايه": 800, "ثمنمايه": 800, "تسعميه": 900, "تسعمايه": 900,
    "metein": 200, "mitin": 200, "teltemeya": 300, "rob3omeya": 400, "khomsomeya": 500, "5omsomeya": 500,
}
THOUSAND_MULT: dict[str, int] = {
    "الف": 1000, "الاف": 1000, "تلاف": 1000, "الوف": 1000,
    "thousand": 1000, "thousands": 1000, "k": 1000, "grand": 1000, "alf": 1000, "talaf": 1000, "alaf": 1000,
}
THOUSAND_FIXED: dict[str, int] = {"الفين": 2000, "الفان": 2000, "alfen": 2000, "alfein": 2000}
MILLION_MULT: dict[str, int] = {
    "مليون": 1_000_000, "ملايين": 1_000_000, "million": 1_000_000, "millions": 1_000_000,
    "mil": 1_000_000, "m": 1_000_000, "milion": 1_000_000, "malyon": 1_000_000,
}
MILLION_FIXED: dict[str, int] = {"مليونين": 2_000_000}
FRACTIONS: dict[str, Decimal] = {
    "نص": D("0.5"), "نصف": D("0.5"), "ربع": D("0.25"), "half": D("0.5"), "quarter": D("0.25"),
    "nos": D("0.5"), "nus": D("0.5"), "noss": D("0.5"), "rob3": D("0.25"),
}
CONNECTORS = {"و", "and", "w", "we"}
# Words that are numbers ONLY before a scale word: "تمن تلاف" = 8000, but "تمن البنزين" = "the price of petrol".
CONSTRUCT_ONLY: dict[str, int] = {"تمن": 8, "ثمن": 8}

# Words after a number that make it a quantity/duration, not money.
QUANTITY_UNITS = {
    "كيلو", "كيلوجرام", "كيلوجرامات", "جرام", "جم", "لتر", "لترات", "قطعه", "قطع", "حته", "حتت",
    "علبه", "علب", "كيس", "اكياس", "كرتونه", "كراتين", "ازازه", "ازايز", "زجاجه", "باكو", "باكت",
    "حبه", "حبات", "رغيف", "ارغفه", "كوبايه", "كوبايات", "متر", "امتار", "نفر", "افراد", "تذاكر",
    "kg", "kgs", "kilo", "kilos", "kilogram", "kilograms", "gram", "grams", "g", "liter", "liters",
    "litre", "litres", "pcs", "pieces", "piece", "items", "item", "boxes", "box", "packs", "pack",
    "bottles", "bottle", "cans", "loaves", "units", "unit", "cups", "cup", "tickets", "people",
    "persons", "meters", "metres", "x", "times", "مرات", "مره",
}
DURATION_UNITS = {
    "يوم", "ايام", "يومين", "اسبوع", "اسابيع", "شهر", "شهور", "اشهر", "سنه", "سنين", "سنوات",
    "ساعات", "دقايق", "دقيقه", "دقيقتين", "ليالي", "ليله", "days", "day", "weeks", "week", "months",
    "month", "years", "year", "hours", "hour", "minutes", "minute", "mins", "nights", "night",
    "pm", "am", "p.m", "a.m", "o'clock", "oclock", "مساء", "صباحا", "ayam", "yom",
}
PIASTER_WORDS = {"قرش", "صاغ", "piasters", "piaster", "piastres", "2ersh", "cents", "cent", "سنت"}
TIME_PREFIX_WORDS = {"الساعه", "ساعه", "around", "by", "about", "el sa3a", "elsa3a", "sa3a"}
ID_PREFIX_WORDS = {"رقم", "number", "no", "#", "route", "دور", "الدور", "floor", "room", "اوضه", "شقه", "apartment"}

PAY_VERBS = {
    "دفعت", "دفع", "دفعنا", "دفعتلهم", "دفعتله", "دفعتلها", "صرفت", "صرف", "صرفنا", "اشتريت", "اشترينا",
    "اشتري", "جبت", "جبنا", "حاسبت", "حاسب", "حاسبنا", "اديت", "ادفع", "شحنت", "طلبت", "ركبت", "خلصت",
    "paid", "pay", "spent", "spend", "bought", "buy", "cost", "costs", "charged", "ordered", "topped",
    "dafa3t", "dafaat", "dfa3t", "saraft", "sraft", "eshtarit", "eshtareet", "eshtaret", "gebt", "7asebt",
}
INCOME_VERBS = {
    "قبضت", "قبض", "استلمت", "اتحولي", "اتحولتلي", "حولولي", "جالي", "جاتلي", "وصلني", "وصلتني", "كسبت",
    "received", "got", "earned", "receive", "2abadt", "estalamt", "et7awelly",
}
AMOUNT_PREPOSITIONS = {"ب", "بمبلغ", "بسعر", "بقيمه", "مبلغ", "قيمه", "سعر", "for", "of", "b", "bi", "be", "worth", "totalling", "totaling", "amount"}

_ALLOWED_NUMBER_PREFIXES = ("و", "ب", "وب")


@dataclass
class NumberSpan:
    """A number found in the token list: tokens[start:end] mean `value`."""

    value: Decimal
    start: int
    end: int
    text: str
    has_words: bool = False
    last_scale: int = 1


@dataclass
class AmountResult:
    """The chosen money amount (or None) and why."""

    value: Optional[Decimal]
    confidence: float
    span: Optional[NumberSpan] = None
    currency_span_index: Optional[int] = None
    ambiguous: bool = False
    reason: str = ""
    candidates: list[tuple[Decimal, float]] = field(default_factory=list)
    consumed: set[int] = field(default_factory=set)


# ---------------------------------------------------------------------------
# Digits
# ---------------------------------------------------------------------------
def parse_digit_token(s: str) -> Optional[Decimal]:
    """Parse "150", "1,500", "1.500", "12.50", "12,50", "1,500.75". Dates/times return None."""
    if not s or not s[0].isdigit():
        return None
    if any(c in s for c in ":/") or s.count("-") > 0:
        return None
    t = s
    try:
        if "," in t and "." in t:
            if t.rfind(",") < t.rfind("."):
                t = t.replace(",", "")
            else:
                t = t.replace(".", "").replace(",", ".")
        elif "," in t:
            parts = t.split(",")
            if all(len(p) == 3 for p in parts[1:]):
                t = t.replace(",", "")
            elif len(parts) == 2 and len(parts[1]) in (1, 2):
                t = parts[0] + "." + parts[1]
            else:
                t = t.replace(",", "")
        elif "." in t:
            parts = t.split(".")
            if len(parts) > 2:
                if all(len(p) == 3 for p in parts[1:]):
                    t = t.replace(".", "")
                else:
                    return None
            elif len(parts[1]) == 3 and 1 <= len(parts[0]) <= 3 and parts[0] != "0":
                t = parts[0] + parts[1]
        return Decimal(t)
    except (InvalidOperation, ValueError):
        return None


# ---------------------------------------------------------------------------
# Word lookup
# ---------------------------------------------------------------------------
def _classify(word: str) -> Optional[tuple[str, Decimal]]:
    if word in UNITS:
        return "unit", D(UNITS[word])
    if word in TEENS:
        return "unit", D(TEENS[word])
    if word in TENS:
        return "unit", D(TENS[word])
    if word in HUNDRED_MULT:
        return "hundred", D(HUNDRED_MULT[word])
    if word in HUNDRED_FIXED:
        return "hundred_fixed", D(HUNDRED_FIXED[word])
    if word in THOUSAND_MULT:
        return "thousand", D(THOUSAND_MULT[word])
    if word in THOUSAND_FIXED:
        return "thousand_fixed", D(THOUSAND_FIXED[word])
    if word in MILLION_MULT:
        return "million", D(MILLION_MULT[word])
    if word in MILLION_FIXED:
        return "million_fixed", D(MILLION_FIXED[word])
    if word in FRACTIONS:
        return "fraction", FRACTIONS[word]
    return None


def lookup_number_word(folded: str) -> Optional[tuple[str, Decimal, bool]]:
    """Return (kind, value, had_connector_prefix) for a folded word, or None.

    Handles attached "و" (and) / "ب" (for): "وخمسمية" -> ("hundred_fixed", 500, True).
    The single letters "m"/"k" only count when they follow a digit (checked by the caller).
    """
    hit = _classify(folded)
    if hit:
        return hit[0], hit[1], False
    if "-" in folded:  # "twenty-five"
        parts = [_classify(p) for p in folded.split("-") if p]
        if parts and all(p is not None and p[0] == "unit" for p in parts):
            return "unit", sum((p[1] for p in parts if p is not None), D(0)), False
    for p in _ALLOWED_NUMBER_PREFIXES:
        if folded.startswith(p) and len(folded) - len(p) >= 2:
            hit = _classify(folded[len(p):])
            if hit:
                return hit[0], hit[1], p.startswith("و")
    return None


def is_number_word(folded: str) -> bool:
    return lookup_number_word(folded) is not None


# ---------------------------------------------------------------------------
# Span parser
# ---------------------------------------------------------------------------
def _parse_at(tokens: list[Token], i: int, skip: set[int]) -> Optional[NumberSpan]:
    """Greedy parse of one number starting at tokens[i]."""
    total = D(0)
    current = D(0)
    have_any = False
    has_words = False
    last_scale = 1
    last_was_digit = False
    pending_connector = False
    j = i
    n = len(tokens)
    while j < n and j not in skip:
        tok = tokens[j]
        f = tok.fold
        # Connector ("و", "and"): only consumed when a number word follows.
        if have_any and f in CONNECTORS:
            if j + 1 < n and (j + 1) not in skip:
                nxt = tokens[j + 1].fold
                nxt_hit = lookup_number_word(nxt)
                if nxt == "a" and j + 2 < n and tokens[j + 2].fold in ("half", "quarter"):
                    pending_connector = True
                    j += 2  # skip "and a"
                    continue
                if nxt_hit and not (nxt_hit[0] == "unit" and last_was_digit and last_scale == 1):
                    pending_connector = True
                    j += 1
                    continue
                if tokens[j + 1].is_number and last_scale >= 100:
                    v = parse_digit_token(tokens[j + 1].text)
                    if v is not None and v < last_scale:
                        pending_connector = True
                        j += 1
                        continue
            break
        # "a hundred", "a thousand"
        if not have_any and f == "a" and j + 1 < n and tokens[j + 1].fold in ("hundred", "thousand"):
            j += 1
            continue
        # "الا ربع" = minus a quarter: "ألف إلا ربع" = 750
        if have_any and f in ("الا", "illa", "ella") and j + 1 < n and tokens[j + 1].fold == "ربع":
            scale = last_scale if last_scale >= 100 else 1
            current = current - D("0.25") * scale if current else current
            if not current:
                total = total - D("0.25") * scale
            has_words = True
            j += 2
            break
        if tok.is_number:
            v = parse_digit_token(tok.text)
            if v is None:
                break
            if have_any and not pending_connector:
                break
            if have_any and pending_connector:
                current += v
            else:
                current = v
            have_any = True
            last_was_digit = True
            pending_connector = False
            j += 1
            continue
        hit = lookup_number_word(f)
        if hit is None and f in CONSTRUCT_ONLY and j + 1 < n:
            nxt_hit = lookup_number_word(tokens[j + 1].fold)
            if nxt_hit and nxt_hit[0] in ("hundred", "thousand"):
                hit = ("unit", D(CONSTRUCT_ONLY[f]), False)
        if hit is None:
            break
        kind, value, had_conn = hit
        if f in ("m", "k") and not last_was_digit:
            break  # a lone "m"/"k" is a letter, not a multiplier
        if had_conn and not have_any:
            # "وخمسين" at the very start is still a number ("و" = and).
            pass
        if had_conn and have_any:
            pending_connector = True
        if have_any and not pending_connector and kind == "unit" and last_was_digit:
            break  # "150 five" -> two separate numbers
        if kind == "unit":
            if have_any and not pending_connector and current and current % 10 != 0 and not last_was_digit:
                # two unit words in a row ("اتنين تلاتة") -> stop
                if value < 10:
                    break
            current += value
        elif kind == "hundred":
            if current == 0:
                current = value
            elif current < 100 and (current < 10 or f in ("hundred", "hundreds")):
                current = current * value
            else:
                current += value
            last_scale = 100
        elif kind == "hundred_fixed":
            current += value
            last_scale = 100
        elif kind == "thousand":
            if current == 0:
                current = D(1)
            total += current * value
            current = D(0)
            last_scale = 1000
        elif kind == "thousand_fixed":
            total += value + current * 1000 if current else value
            current = D(0)
            last_scale = 1000
        elif kind == "million":
            base = total + current
            if base == 0:
                base = D(1)
            total = base * value
            current = D(0)
            last_scale = 1_000_000
        elif kind == "million_fixed":
            total += value
            current = D(0)
            last_scale = 1_000_000
        elif kind == "fraction":
            if not have_any or not pending_connector:
                break
            scale = last_scale if last_scale >= 100 else 1
            current += value * scale
            has_words = True
            have_any = True
            pending_connector = False
            j += 1
            # "two and a half thousand" -> keep going so "thousand" multiplies 2.5
            if j < n and j not in skip:
                nxt_hit = lookup_number_word(tokens[j].fold)
                if nxt_hit and nxt_hit[0] in ("thousand", "million") and scale == 1:
                    continue
            break
        have_any = True
        has_words = True
        last_was_digit = False
        pending_connector = False
        j += 1
    if not have_any:
        return None
    value = total + current
    text = " ".join(t.text for t in tokens[i:j])
    return NumberSpan(value=value, start=i, end=j, text=text, has_words=has_words, last_scale=last_scale)


def find_numbers(tokens: list[Token], skip: Optional[Iterable[int]] = None) -> list[NumberSpan]:
    """Find all number spans, ignoring token indices in `skip` (merchant names, dates...)."""
    skip_set = set(skip or ())
    spans: list[NumberSpan] = []
    i = 0
    while i < len(tokens):
        if i in skip_set:
            i += 1
            continue
        f = tokens[i].fold
        # A lone "a"/"and"/"و" never starts a number unless "a hundred"; a lone fraction word
        # ("نص كيلو") is not an amount either.
        if f in CONNECTORS or (lookup_number_word(f) or ("", 0, False))[0] == "fraction":
            i += 1
            continue
        span = _parse_at(tokens, i, skip_set)
        if span is None or span.end == span.start:
            i += 1
            continue
        if span.value > 0:
            spans.append(span)
        i = span.end
    return spans


def parse_number(text: str) -> Optional[Decimal]:
    """Convenience: parse the FIRST number in a phrase ("ألف ونص" -> 1500)."""
    from .normalize import normalize_text, tokenize

    spans = find_numbers(tokenize(normalize_text(text)))
    return spans[0].value if spans else None


# ---------------------------------------------------------------------------
# Choosing the amount
# ---------------------------------------------------------------------------
def _tail_fraction(tokens: list[Token], k: int) -> tuple[Decimal, int]:
    """After a currency word: "ونص" / "و نص" / "and a half" / "و خمسين قرش". Returns (extra, tokens_used)."""
    n = len(tokens)
    if k >= n:
        return D(0), 0
    f = tokens[k].fold
    if f in ("ونص", "ونصف"):
        return D("0.5"), 1
    if f in ("وربع",):
        return D("0.25"), 1
    if f in CONNECTORS and k + 1 < n:
        g = tokens[k + 1].fold
        if g in ("نص", "نصف", "half"):
            return D("0.5"), 2
        if g == "ربع":
            return D("0.25"), 2
        if g == "a" and k + 2 < n and tokens[k + 2].fold == "half":
            return D("0.5"), 3
        # "و خمسين قرش"
        sub = _parse_at(tokens, k + 1, set())
        if sub and sub.end < n and tokens[sub.end].fold in PIASTER_WORDS and sub.value < 100:
            return sub.value / 100, sub.end - k + 1
    # "وخمسين قرش"
    hit = lookup_number_word(f)
    if hit and hit[2]:
        sub = _parse_at(tokens, k, set())
        if sub and sub.end < n and tokens[sub.end].fold in PIASTER_WORDS and sub.value < 100:
            return sub.value / 100, sub.end - k + 1
    return D(0), 0


def select_amount(
    tokens: list[Token],
    spans: list[NumberSpan],
    currency_spans: list[tuple[int, int, str]],
    month_indices: Optional[set[int]] = None,
    date_indices: Optional[set[int]] = None,
) -> AmountResult:
    """Score every number span and return the most likely money amount.

    currency_spans: (start, end, code) token ranges of currency words.
    month_indices:  token indices of month names (numbers next to them are dates).
    """
    month_indices = month_indices or set()
    date_indices = date_indices or set()
    cur_by_start = {s: (s, e, c) for (s, e, c) in currency_spans}
    cur_by_end = {e: (s, e, c) for (s, e, c) in currency_spans}
    scored: list[tuple[float, float, NumberSpan, Optional[int], str]] = []
    excluded_reasons: list[str] = []
    for sp in spans:
        prev_f = tokens[sp.start - 1].fold if sp.start > 0 else ""
        prev2_f = tokens[sp.start - 2].fold if sp.start > 1 else ""
        next_f = tokens[sp.end].fold if sp.end < len(tokens) else ""
        # --- hard exclusions ---------------------------------------------------
        # "300 يوم 3": the "يوم" belongs to a date expression, so 300 is not "300 days".
        next_is_date = sp.end in date_indices and next_f not in ("pm", "am", "p.m", "a.m")
        if next_f in QUANTITY_UNITS or (next_f in DURATION_UNITS and not next_is_date):
            excluded_reasons.append(f"{sp.text}: quantity/duration")
            continue
        if next_f in PIASTER_WORDS:
            excluded_reasons.append(f"{sp.text}: piasters")
            continue
        if prev_f in TIME_PREFIX_WORDS or prev_f in ID_PREFIX_WORDS:
            excluded_reasons.append(f"{sp.text}: time or id")
            continue
        if (sp.end in month_indices) or ((sp.start - 1) in month_indices):
            excluded_reasons.append(f"{sp.text}: date")
            continue
        # --- scoring ------------------------------------------------------------
        score = 0.3
        conf = 0.6
        reason = "bare number"
        cur_idx: Optional[int] = None
        if sp.end in cur_by_start:
            cur_idx = sp.end
            score += 0.6
            conf = 0.95
            reason = "next to currency word"
        elif sp.start in cur_by_end:
            cur_idx = cur_by_end[sp.start][0]
            score += 0.6
            conf = 0.95
            reason = "after currency symbol/word"
        if prev_f in AMOUNT_PREPOSITIONS:
            score += 0.3
            if conf < 0.85:
                conf, reason = 0.85, "after ب/for"
        window = {tokens[k].fold for k in range(max(0, sp.start - 4), sp.start)}
        if window & PAY_VERBS or window & INCOME_VERBS:
            score += 0.15
            if conf < 0.75:
                conf, reason = 0.75, "after pay verb"
        if sp.has_words and sp.value <= 10 and cur_idx is None:
            score -= 0.25  # "واحد صاحبي", "ست" (lady) ...
        if 1990 <= sp.value <= 2035 and sp.value == sp.value.to_integral_value() and cur_idx is None:
            score -= 0.3  # probably a year
        if prev2_f in TIME_PREFIX_WORDS:
            score -= 0.2
        scored.append((score, conf, sp, cur_idx, reason))

    if not scored:
        return AmountResult(value=None, confidence=0.0, reason="no amount found; " + "; ".join(excluded_reasons))

    scored.sort(key=lambda x: (-x[0], x[2].start))
    best_score, conf, best, cur_idx, reason = scored[0]
    ambiguous = False
    if len(scored) > 1:
        second = scored[1][0]
        if best_score - second < 0.15:
            ambiguous = True
            conf = min(conf, 0.45)
        elif cur_idx is None:
            conf = min(conf, 0.7)
    value = best.value
    consumed = set(range(best.start, best.end))
    # "عشرة جنيه ونص" -> 10.50
    if cur_idx is not None and cur_idx >= best.end:
        cur_end = cur_by_start[cur_idx][1]
        extra, used = _tail_fraction(tokens, cur_end)
        if used:
            value += extra
            consumed.update(range(cur_end, cur_end + used))
    return AmountResult(
        value=value,
        confidence=conf,
        span=best,
        currency_span_index=cur_idx,
        ambiguous=ambiguous,
        reason=reason,
        candidates=[(s[2].value, round(s[0], 2)) for s in scored[:3]],
        consumed=consumed,
    )


__all__ = [
    "NumberSpan",
    "AmountResult",
    "parse_digit_token",
    "lookup_number_word",
    "is_number_word",
    "find_numbers",
    "parse_number",
    "select_amount",
    "PAY_VERBS",
    "INCOME_VERBS",
    "QUANTITY_UNITS",
    "fold",
]
