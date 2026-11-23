"""Currency detection.

WHY a separate module: the currency word does two jobs. It tells us the ISO
code (EGP, USD...) AND it is the strongest clue for which number is the
amount ("150 جنيه" is money, "الساعة 3" is not). So we return token spans,
not just a code, and numbers.py uses those spans.

Rules (see docs/DECISIONS.md):
    * No currency mentioned -> EGP (default), with lower confidence.
    * GBP is detected only with "استرليني"/"sterling"/"£"/"gbp", and that check
      runs BEFORE the generic "pound(s)" -> EGP rule.
    * قرش / piasters are never a currency on their own; numbers.py only uses
      them as a fraction ("عشرة جنيه وخمسين قرش" = 10.50).
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from .normalize import Token, fold_phrase, prefix_variants

# Multi-word phrases first (longest match wins). Keys are folded phrases.
_CURRENCY_PHRASES: list[tuple[str, str]] = [
    # GBP first so "جنيه استرليني" / "pounds sterling" never become EGP.
    ("جنيه استرليني", "GBP"), ("جنيهات استرليني", "GBP"), ("استرليني", "GBP"),
    ("pound sterling", "GBP"), ("pounds sterling", "GBP"), ("british pounds", "GBP"),
    ("british pound", "GBP"), ("sterling", "GBP"), ("£", "GBP"), ("gbp", "GBP"),
    # EGP
    ("جنيه مصري", "EGP"), ("egyptian pounds", "EGP"), ("egyptian pound", "EGP"),
    ("ج.م", "EGP"), ("ج م", "EGP"), ("l.e", "EGP"), ("l e", "EGP"),
    ("جنيه", "EGP"), ("جنيهات", "EGP"), ("جنية", "EGP"), ("ج", "EGP"), ("le", "EGP"),
    ("egp", "EGP"), ("pounds", "EGP"), ("pound", "EGP"), ("ginih", "EGP"), ("geneh", "EGP"),
    ("gneh", "EGP"), ("genih", "EGP"), ("gnih", "EGP"), ("geneih", "EGP"), ("ginee", "EGP"),
    ("quid", "GBP"),
    # USD
    ("دولار امريكي", "USD"), ("دولار", "USD"), ("دولارات", "USD"), ("$", "USD"), ("usd", "USD"),
    ("dollars", "USD"), ("dollar", "USD"), ("dolar", "USD"), ("dolars", "USD"), ("bucks", "USD"),
    # EUR
    ("يورو", "EUR"), ("€", "EUR"), ("eur", "EUR"), ("euro", "EUR"), ("euros", "EUR"),
    # SAR
    ("ريال سعودي", "SAR"), ("ريالات سعودي", "SAR"), ("ريال", "SAR"), ("ريالات", "SAR"),
    ("sar", "SAR"), ("riyal", "SAR"), ("riyals", "SAR"), ("saudi riyal", "SAR"), ("saudi riyals", "SAR"),
    # AED
    ("درهم اماراتي", "AED"), ("درهم", "AED"), ("دراهم", "AED"), ("aed", "AED"),
    ("dirham", "AED"), ("dirhams", "AED"),
]

_INDEX: dict[tuple[str, ...], str] = {}
_MAX_LEN = 1


def _build_index() -> None:
    global _MAX_LEN
    if _INDEX:
        return
    for phrase, code in _CURRENCY_PHRASES:
        key = fold_phrase(phrase)
        if key and key not in _INDEX:
            _INDEX[key] = code
            _MAX_LEN = max(_MAX_LEN, len(key))


# Single-letter Arabic "ج" is only a currency right after a number (otherwise it is a letter).
_NEEDS_NUMBER_BEFORE = {("ج",), ("le",), ("l", "e")}


@dataclass
class CurrencySpan:
    code: str
    start: int
    end: int
    text: str


def _first_word_variants(tok: Token) -> list[str]:
    """The token itself plus versions without attached prefixes (بالدولار -> دولار)."""
    out = []
    for _, rest in prefix_variants(tok.fold):
        out.append(rest)
    return out


def find_currencies(tokens: list[Token], skip: Optional[set[int]] = None) -> list[CurrencySpan]:
    """Return every currency mention as a token span (longest match first)."""
    _build_index()
    skip = skip or set()
    spans: list[CurrencySpan] = []
    i = 0
    n = len(tokens)
    while i < n:
        if i in skip:
            i += 1
            continue
        matched = False
        for length in range(min(_MAX_LEN, n - i), 0, -1):
            if any(k in skip for k in range(i, i + length)):
                continue
            rest = tuple(t.fold for t in tokens[i + 1 : i + length])
            for first in _first_word_variants(tokens[i]):
                key = (first,) + rest
                code = _INDEX.get(key)
                if code is None:
                    continue
                if key in _NEEDS_NUMBER_BEFORE:
                    prev = tokens[i - 1] if i > 0 else None
                    if prev is None or not (prev.is_number or _is_number_word(prev.fold)):
                        continue
                spans.append(CurrencySpan(code=code, start=i, end=i + length,
                                          text=" ".join(t.text for t in tokens[i : i + length])))
                i += length
                matched = True
                break
            if matched:
                break
        if not matched:
            i += 1
    return spans


def _is_number_word(f: str) -> bool:
    from .numbers import is_number_word

    return is_number_word(f)


def detect_currency(tokens: list[Token], default: str = "EGP") -> tuple[str, float, list[CurrencySpan]]:
    """Return (code, confidence, spans). Default EGP at 0.7 when nothing is said."""
    spans = find_currencies(tokens)
    if not spans:
        return default, 0.7, spans
    codes = {s.code for s in spans}
    if len(codes) == 1:
        return spans[0].code, 0.95, spans
    # Several currencies in one sentence: take the first, lower confidence.
    return spans[0].code, 0.5, spans
