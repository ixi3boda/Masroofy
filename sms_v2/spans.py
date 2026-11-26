"""Character-span finders and parsers for v2.

Two jobs:
  * offline, for labelling: locate the text span that produced each gold field,
    so the token head has something to learn from;
  * online, at decode time: turn a tagged span back into a value.

This layer deliberately fixes the three rule-layer limits REAL_FORMATS.md calls
unfixable-by-more-data, because they are limits of v1's regexes, not of its
statistics:

  1. numbers glued to currency letters  (195.15EGP, EGP15,608.48, 11260EGP)
     v1's RE_NUM has (?<![A-Za-z])/(?![A-Za-z]) and rejects them outright.
  2. a leading-dot number               (EUR .93)
  3. date formats v1 never knew         (31AUG26, 30-AUG-2026, 08/20/2026 as
                                         MM/DD, Feb 13 2026, 26-10-14 as YY-MM-DD)

Everything here is plain regex + datetime. No model, no dependencies beyond the
standard library, so it can be unit-tested and reused from the Java side later.
"""
import datetime as dt
import re

# ------------------------------------------------------------------ normalization
# Identical to v1's: 1:1 per character, so every offset found here is valid in the
# ORIGINAL text too. Do not add anything that changes string length.
_NORM = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫", "0123456789" "0123456789" ",.")


def bmp(s: str) -> str:
    """Astral-plane chars (emoji) -> U+FFFD, so Python and Java/Kotlin agree on offsets."""
    return "".join(c if ord(c) <= 0xFFFF else "�" for c in s)


def normalize(s: str) -> str:
    return bmp(s).translate(_NORM)


AR = "؀-ۿ"          # Arabic block, as used in v1's character classes

# ------------------------------------------------------------------ currency
# Longest-first so "L.E" wins over "LE" and "ج.م" over "ج".
CURRENCY = [("L.E", "EGP"), ("ج.م", "EGP"), ("EGP", "EGP"), ("USD", "USD"), ("EUR", "EUR"),
            ("GBP", "GBP"), ("SAR", "SAR"), ("AED", "AED"), ("جنيه", "EGP"), ("جنية", "EGP"),
            ("LE", "EGP"), ("جم", "EGP"), ("ج", "EGP")]
RE_CURRENCY = re.compile("|".join(re.escape(t) for t, _ in CURRENCY))
CURRENCY_CODE = {t.lower(): c for t, c in CURRENCY}


def currency_spans(n):
    """Every currency token in the text: (start, end, code)."""
    out = []
    for m in RE_CURRENCY.finditer(n):
        tok = m.group(0)
        # "ج" and "LE" are single/short tokens that also occur inside words; require
        # that they are not glued to another letter of the same script.
        if tok in ("ج", "جم", "LE"):
            before = n[m.start() - 1] if m.start() else " "
            after = n[m.end()] if m.end() < len(n) else " "
            same_script = (lambda c: bool(re.match(f"[{AR}]", c)) if tok != "LE"
                           else bool(re.match("[A-Za-z]", c)))
            if same_script(before) or same_script(after):
                continue
        out.append((m.start(), m.end(), CURRENCY_CODE[tok.lower()]))
    return out


def currency_for(n, amount_span, max_gap=4):
    """Currency code for an amount span: the nearest currency token on either side.

    Unlike v1's currency_near() this allows a gap of 0 characters, which is what
    makes EGP450.00 and 195.15EGP work.
    """
    if amount_span is None:
        return None
    s, e = amount_span
    best, best_d = None, 10 ** 6
    for cs, ce, code in currency_spans(n):
        if ce <= s:
            d = s - ce
        elif cs >= e:
            d = cs - e
        else:
            d = 0
        if d <= max_gap and d < best_d:
            best, best_d = code, d
    return best


# ------------------------------------------------------------------ numbers
# v1: (?<![A-Za-z\d.,]) ... (?![A-Za-z\d])   -- letters on either side kill the match.
# v2: only digits/./, block a match, so a number glued to EGP still parses. A bare
# leading-dot number (.93) is a candidate too.
RE_NUM = re.compile(r"(?<![\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d{1,4})?|\d*\.\d{1,4}|\d+)(?!\d)")
RE_MASKED_NUM = re.compile(r"(?<![A-Za-z])[xX*#]{1,4}(\d{3,4})(?!\d)")


def _to_float(txt):
    try:
        return float(txt.replace(",", ""))
    except ValueError:
        return None


def number_spans(n, mask=()):
    """Every number candidate: (start, end, text, value), skipping masked regions
    (dates and times, whose digits are not amounts)."""
    out, seen = [], set()
    for m in RE_MASKED_NUM.finditer(n):
        s, e = m.span(1)
        out.append((s, e, m.group(1), float(m.group(1))))
        seen.add((s, e))
    for m in RE_NUM.finditer(n):
        s, e = m.span(1)
        if (s, e) in seen or any(a <= s < b for a, b in mask):
            continue
        val = _to_float(m.group(1))
        if val is None:
            continue
        out.append((s, e, m.group(1), val))
    return sorted(out)


# ------------------------------------------------------------------ dates and times
MON_EN = {m: i + 1 for i, m in enumerate(
    "jan feb mar apr may jun jul aug sep oct nov dec".split())}
MON_EN_FULL = {m: i + 1 for i, m in enumerate(
    "january february march april may june july august september october november december".split())}
MON_AR = {m: i + 1 for i, m in enumerate(
    ["يناير", "فبراير", "مارس", "أبريل", "مايو", "يونيو", "يوليو",
     "أغسطس", "سبتمبر", "أكتوبر", "نوفمبر", "ديسمبر"])}
MON_AR.update({"ابريل": 4, "اكتوبر": 10, "اغسطس": 8, "مايو": 5})

_AR_MON_ALT = "|".join(sorted(MON_AR, key=len, reverse=True))

# 10/08/26, 2026-08-10, 08.20.2026 — three numeric parts, order resolved below.
RE_NUM3 = re.compile(r"(?<![\d/.\-])(\d{1,4})([/.\-])(\d{1,2})\2(\d{1,4})(?![\d/])")
# 31AUG26 (HSBC), 30-AUG-2026 (Banque Misr), 13 Feb 2026, 4 أكتوبر 2026
RE_DMON = re.compile(r"(?<![A-Za-z\d])(\d{1,2})\s*[-\s]?\s*([A-Za-z]{3,9}|" + _AR_MON_ALT +
                     r")\s*[-,\s]?\s*(\d{2,4})(?![A-Za-z\d])")
# Feb 13, 2026 (Vodafone Cash)
RE_MOND = re.compile(r"(?<![A-Za-z\d])([A-Za-z]{3,9}|" + _AR_MON_ALT +
                     r")\s+(\d{1,2}),?\s+(\d{4})(?!\d)")
RE_TIME = re.compile(r"(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?::([0-5]\d))?"
                     r"(?:\s*(AM|PM|am|pm|ص|م)(?![\w]))?(?!\d)")

REF_YEAR = 2026        # the dataset's era; only used to break genuine ambiguity


def _month(name):
    k = name.lower()
    return MON_AR.get(name) or MON_EN_FULL.get(k) or MON_EN.get(k[:3])


def _year(y):
    return y + 2000 if y < 100 else y


def _mk(y, m, d):
    try:
        return dt.date(y, m, d)
    except ValueError:
        return None


def _resolve3(a, b, c, ref_year=REF_YEAR):
    """Pick a reading for a three-part numeric date.

    Candidates in preference order: day-first (Egyptian convention), then
    month-first, then year-first. Among the ones that produce a real date, the
    winner is whichever lands nearest `ref_year`; ties keep the earlier
    preference. That is what tells 08/20/2026 (MM/DD, day-first impossible) from
    10/08/26 (DD/MM/YY) from Vodafone Cash's 26-10-14 (YY-MM-DD: day-first would
    give 2014, fourteen years off).
    """
    cands = []
    if c > 31 or c < 100:                       # a,b,c = d,m,y
        cands.append(("dmy", _mk(_year(c), b, a)))
        cands.append(("mdy", _mk(_year(c), a, b)))
    if a >= 1000 or a < 100:                    # a,b,c = y,m,d
        cands.append(("ymd", _mk(_year(a), b, c)))
    best, best_key = None, None
    for i, (_, d) in enumerate(cands):
        if d is None:
            continue
        key = (abs(d.year - ref_year), i)
        if best_key is None or key < best_key:
            best, best_key = d, key
    return best


def date_spans(n, ref_year=REF_YEAR):
    """Every date in the text: (start, end, date | None). None where the format is
    recognisable but incomplete (NBE's `يوم 04-17` has no year), which the gold
    data also leaves as null."""
    out = []
    for m in RE_NUM3.finditer(n):
        out.append((m.start(), m.end(),
                    _resolve3(int(m.group(1)), int(m.group(3)), int(m.group(4)), ref_year)))
    for m in RE_DMON.finditer(n):
        mo = _month(m.group(2))
        if mo:
            out.append((m.start(), m.end(), _mk(_year(int(m.group(3))), mo, int(m.group(1)))))
    for m in RE_MOND.finditer(n):
        mo = _month(m.group(1))
        if mo:
            out.append((m.start(), m.end(), _mk(int(m.group(3)), mo, int(m.group(2)))))
    # two-part day-month with no year (يوم 04-17) -> a span, but no date
    for m in re.finditer(r"(?<![\d/.\-])(\d{1,2})([/\-])(\d{1,2})(?![\d/\-])", n):
        if not any(a <= m.start() < b for a, b, _ in out):
            out.append((m.start(), m.end(), None))
    return sorted(set(out), key=lambda t: (t[0], t[1]))


def time_spans(n):
    out = []
    for m in RE_TIME.finditer(n):
        h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(4)
        if ap:
            pm = ap.lower() in ("pm", "م")
            if h == 12:
                h = 0
            if pm:
                h += 12
        if h > 23:
            continue
        out.append((m.start(), m.end(), dt.time(h, mi)))
    return out


def parse_date_text(s, ref_year=REF_YEAR):
    """Parse a span the model tagged as DATE. Returns a date or None."""
    got = date_spans(normalize(s), ref_year)
    for _, _, d in got:
        if d is not None:
            return d
    return None


def parse_time_text(s):
    got = time_spans(normalize(s))
    return got[0][2] if got else None


def iso(date, time=None):
    """The exact datetime format v1 emits, so the strings compare equal."""
    if date is None:
        return None
    if time is None:
        return date.isoformat()
    return dt.datetime.combine(date, time).strftime("%Y-%m-%dT%H:%M:00")


# ------------------------------------------------------------------ labelling helpers
def masked_regions(n, ref_year=REF_YEAR):
    """Date and time spans, whose digits must not be offered as amount candidates."""
    return [(s, e) for s, e, _ in date_spans(n, ref_year)] + [(s, e) for s, e, _ in time_spans(n)]


def role_spans(n, expected):
    """Map gold numeric fields back to character spans.

    Mirrors v1's num_labels(): match by value, first unused candidate wins, so the
    two implementations are labelled from the same evidence.
    """
    cands = number_spans(n, masked_regions(n))
    out, used = {}, set()
    def take(role, test):
        for s, e, txt, val in cands:
            if (s, e) in used:
                continue
            if test(txt, val):
                used.add((s, e))
                out[role] = (s, e)
                return
    amt, fee = expected.get("amount"), expected.get("fee")
    bal, last4 = expected.get("balance_after"), expected.get("account_last4")
    if amt is not None:
        take("AMOUNT", lambda t, v: abs(v - amt) < 1e-6)
    if fee is not None:
        # fee == 0.0 is usually a literal "0" in the text ("مصاريف الخدمة 0 جنيه"),
        # so it must be labelled; only a fee stated in words has no span, and
        # pipeline.NO_FEE covers that.
        take("FEE", lambda t, v: abs(v - fee) < 1e-6)
    if bal is not None:
        take("BALANCE", lambda t, v: abs(v - bal) < 1e-6)
    if last4:
        take("LAST4", lambda t, v: t == last4)
        if "LAST4" not in out:
            # Banque Misr prints the whole 16-digit account ("رقم 7490606815708931")
            # and gold keeps only the last four. Tag just those four characters.
            for s, e, txt, _ in cands:
                if (s, e) in used or not txt.isdigit() or not txt.endswith(last4):
                    continue
                if len(txt) > len(last4):
                    out["LAST4"] = (e - len(last4), e)
                    used.add((s, e))
                    break
    return out


def gold_spans(text, expected, ref_year=REF_YEAR):
    """Every character span to tag for one training record: {TAG: (start, end)}.

    `text` must already be bmp()-ed; offsets are valid in it and in its
    normalize()d twin.
    """
    n = normalize(text)
    spans = role_spans(n, expected)

    merchant = expected.get("merchant")
    if merchant:
        i = text.find(merchant)
        if i >= 0:
            spans["MERCHANT"] = (i, i + len(merchant))

    want = expected.get("datetime")
    if want:
        d = dt.date.fromisoformat(want[:10])
        for s, e, got in date_spans(n, ref_year):
            if got == d:
                spans["DATE"] = (s, e)
                break
        if len(want) > 10:
            t = dt.time.fromisoformat(want[11:])
            for s, e, got in time_spans(n):
                if got == t:
                    spans["TIME"] = (s, e)
                    break

    cur = expected.get("currency")
    if cur and "AMOUNT" in spans:
        a_s, a_e = spans["AMOUNT"]
        best, best_d = None, 10 ** 6
        for cs, ce, code in currency_spans(n):
            if code != cur:
                continue
            d = a_s - ce if ce <= a_s else (cs - a_e if cs >= a_e else 0)
            if 0 <= d < best_d:
                best, best_d = (cs, ce), d
        if best and best_d <= 8:
            spans["CURRENCY"] = best
    return spans
