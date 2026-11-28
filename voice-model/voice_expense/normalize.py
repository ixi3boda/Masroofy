"""Text normalization for Egyptian Arabic, English and code-switched input.

WHY normalize at all?
    The same word can be written many ways: "أوبر" / "اوبر", "جنية" / "جنيه",
    "١٥٠" / "150", "بـ150" / "ب 150". Whisper also mixes these. If we matched
    raw text we would need every spelling in every dictionary. Instead we
    convert text to ONE canonical form and match on that.

Two levels are used:
    * `normalize_text()`  -> readable text, shown to the user as `normalized_text`.
      Digits are Western, diacritics removed, alef unified, Latin lowercased,
      glued tokens split ("150ج" -> "150 ج"). Ta marbuta (ة) is KEPT.
    * `fold()`            -> a stricter key used ONLY for dictionary lookups:
      ة->ه, ى->ي, ؤ->و, ئ->ي, a trailing standalone hamza is dropped
      ("دواء" -> "دوا", "عشاء" -> "عشا"), so MSA and Egyptian spellings meet.

Franco-Arabic ("dafa3t", "embare7", "2akl") uses digits as letters, so we never
split digits away from Latin letters, except for a short list of real unit
suffixes such as "150le", "2.5k", "5pm".
"""
from __future__ import annotations

import re
from dataclasses import dataclass

# --- character tables -------------------------------------------------------
_EASTERN_DIGITS = "٠١٢٣٤٥٦٧٨٩"
_PERSIAN_DIGITS = "۰۱۲۳۴۵۶۷۸۹"
_DIGIT_TABLE = {ord(c): str(i) for i, c in enumerate(_EASTERN_DIGITS)}
_DIGIT_TABLE.update({ord(c): str(i) for i, c in enumerate(_PERSIAN_DIGITS)})
_DIGIT_TABLE[ord("٫")] = "."  # Arabic decimal separator
_DIGIT_TABLE[ord("٬")] = None  # Arabic thousands separator -> removed
_DIGIT_TABLE[ord("،")] = ","  # Arabic comma (kept as punctuation)
_DIGIT_TABLE[ord("؛")] = ";"
_DIGIT_TABLE[ord("؟")] = "?"

# Tashkeel (harakat), superscript alef and Quranic marks, plus tatweel.
_DIACRITICS_RE = re.compile("[ؐ-ًؚ-ٰٟۖ-ۭـ]")
_ALEF_TABLE = {ord("أ"): "ا", ord("إ"): "ا", ord("آ"): "ا", ord("ٱ"): "ا"}
_FOLD_TABLE = {ord("ة"): "ه", ord("ى"): "ي", ord("ؤ"): "و", ord("ئ"): "ي"}

ARABIC_LETTERS = "ء-غف-يٱ-ۓۺ-ۿ"
LATIN_LETTERS = "a-zà-öø-ÿ"
_ARABIC_CHAR = re.compile(f"[{ARABIC_LETTERS}]")
_LATIN_CHAR = re.compile(f"[{LATIN_LETTERS}A-Z]")

# Unit suffixes that may be glued to a number in Latin script: "150le", "2.5k", "5pm".
_LATIN_SUFFIXES = (
    "l\\.e\\.?|le|egp|usd|eur|sar|aed|gbp|k|pm|am|p\\.m\\.?|a\\.m\\.?|kg|kgs|kilo|pcs|"
    "pounds|pound|dollars|dollar|euros|euro|bucks|ginih|geneh|gneh|million|m"
)
_GLUED_LATIN_RE = re.compile(rf"(?<![{LATIN_LETTERS}\d])(\d+(?:[.,]\d+)?)({_LATIN_SUFFIXES})(?![{LATIN_LETTERS}\d])")
_AR_DIGIT_RE = re.compile(f"([{ARABIC_LETTERS}])(\\d)")
_DIGIT_AR_RE = re.compile(f"(\\d)([{ARABIC_LETTERS}])")
_AR_LATIN_RE = re.compile(f"([{ARABIC_LETTERS}])([{LATIN_LETTERS}])")
_LATIN_AR_RE = re.compile(f"([{LATIN_LETTERS}])([{ARABIC_LETTERS}])")
_SYMBOL_RE = re.compile(r"\s*([$€£])\s*")
_ALEF_MAQSURA_END_RE = re.compile(r"ى(?=\s|$|[^\w])")
_SPACES_RE = re.compile(r"\s+")

# Tokens: currency symbols | numbers with separators | Arabic words (may contain a dot: ج.م)
# | Latin/Franco words (may contain digits and . & ' - inside: b.tech, h&m, e&, dafa3t, osn+).
_TOKEN_RE = re.compile(
    rf"[$€£]"
    rf"|\d+(?:[.,:/\-]\d+)*(?![{LATIN_LETTERS}\d])"
    rf"|[{ARABIC_LETTERS}]+(?:\.[{ARABIC_LETTERS}]+)*"
    rf"|[{LATIN_LETTERS}\d]+(?:[.&'’\-][{LATIN_LETTERS}\d]+)*[&+]?"
)


@dataclass
class Token:
    """One word/number of the normalized text.

    text:  the token as it appears in normalized_text
    fold:  the matching key (see `fold`)
    index: position in the token list
    """

    text: str
    fold: str
    index: int
    start: int
    end: int

    @property
    def is_number(self) -> bool:
        return self.text[:1].isdigit() and all(ch.isdigit() or ch in ".,:/-" for ch in self.text)

    @property
    def is_arabic(self) -> bool:
        return bool(_ARABIC_CHAR.search(self.text))

    @property
    def is_latin(self) -> bool:
        return bool(_LATIN_CHAR.search(self.text)) and not self.is_arabic


def normalize_digits(text: str) -> str:
    """Convert Eastern Arabic / Persian digits to 0-9 and Arabic separators to ASCII."""
    return text.translate(_DIGIT_TABLE)


def remove_diacritics(text: str) -> str:
    """Remove tashkeel and tatweel: "بـ١٥٠" -> "ب١٥٠", "جُنَيْه" -> "جنيه"."""
    return _DIACRITICS_RE.sub("", text)


def unify_alef(text: str) -> str:
    return text.translate(_ALEF_TABLE)


def normalize_text(text: str) -> str:
    """Return the readable normalized text used for all matching.

    Steps: digits -> ASCII, remove diacritics/tatweel, unify alef, ى -> ي at the
    end of words, lowercase Latin, split glued tokens, collapse spaces.
    """
    if not text:
        return ""
    t = normalize_digits(text)
    t = remove_diacritics(t)
    t = unify_alef(t)
    t = _ALEF_MAQSURA_END_RE.sub("ي", t)
    t = t.lower()
    # Remove thousands commas written as "1,500" only when followed by exactly 3 digits
    # is handled in numbers.py; here we only split glued tokens.
    t = _GLUED_LATIN_RE.sub(r"\1 \2", t)
    t = _AR_DIGIT_RE.sub(r"\1 \2", t)
    t = _DIGIT_AR_RE.sub(r"\1 \2", t)
    t = _AR_LATIN_RE.sub(r"\1 \2", t)
    t = _LATIN_AR_RE.sub(r"\1 \2", t)
    t = _SYMBOL_RE.sub(r" \1 ", t)
    t = _SPACES_RE.sub(" ", t).strip()
    return t


def fold(word: str) -> str:
    """Stricter matching key for one word or phrase (never shown to the user)."""
    if not word:
        return ""
    w = unify_alef(remove_diacritics(normalize_digits(word))).lower().translate(_FOLD_TABLE)
    w = w.replace("’", "'")
    # Drop a standalone trailing hamza: دواء -> دوا, عشاء -> عشا, كهرباء -> كهربا.
    if len(w) > 2 and w.endswith("ء"):
        w = w[:-1]
    return w


def tokenize(text: str) -> list[Token]:
    """Split already-normalized text into tokens (see `_TOKEN_RE`)."""
    tokens: list[Token] = []
    for m in _TOKEN_RE.finditer(text):
        tok = m.group(0)
        tokens.append(Token(text=tok, fold=fold(tok), index=len(tokens), start=m.start(), end=m.end()))
    return tokens


def fold_phrase(phrase: str) -> tuple[str, ...]:
    """Normalize + tokenize + fold a dictionary phrase into a tuple of keys."""
    return tuple(t.fold for t in tokenize(normalize_text(phrase)))


# Arabic prefixes that attach to the next word. Longest first.
# "لل" is ل + ال contracted (للدكتور = ل + الدكتور).
_AR_PREFIXES = ("وبال", "وال", "بال", "فال", "كال", "لل", "ال", "وب", "ول", "وف", "و", "ف", "ب", "ل", "ك")
# Prefixes that carry the meaning of a preposition (في / ب / ل / من-like).
PREPOSITION_PREFIXES = {"ف", "ب", "ل", "بال", "فال", "لل", "وب", "ول", "وف", "وبال"}


def prefix_variants(folded: str) -> list[tuple[str, str]]:
    """All (prefix, rest) splits of an Arabic word, starting with ("", word).

    Example: "بالفيزا" -> [("", "بالفيزا"), ("بال", "فيزا"), ("بال", "الفيزا"), ("ب", "الفيزا")]
    The caller tries each `rest` against its dictionary.
    """
    out: list[tuple[str, str]] = [("", folded)]
    if not folded or not _ARABIC_CHAR.match(folded):
        return out
    seen = {folded}
    for p in _AR_PREFIXES:
        if folded.startswith(p) and len(folded) - len(p) >= 2:
            rest = folded[len(p):]
            candidates = [rest]
            if p.endswith("ال") or p == "لل":
                candidates.append("ال" + rest)
            for c in candidates:
                if c not in seen:
                    seen.add(c)
                    out.append((p, c))
    return out


def detect_language(text: str) -> str:
    """Return "ar", "en" or "mixed" from the script of the words.

    WHY word-level: one Latin brand name inside an Arabic sentence ("في Uber")
    is exactly what code-switching means, so any mix of Arabic-script words and
    Latin-script words counts as "mixed". Franco-Arabic (Latin letters only)
    is reported as "en" because the schema has no separate value; the dataset
    keeps a separate "franco" group for evaluation.
    """
    ar_words = 0
    latin_words = 0
    for tok in tokenize(normalize_text(text)):
        if tok.is_arabic:
            ar_words += 1
        elif tok.is_latin:
            latin_words += 1
    if latin_words == 0:
        return "ar"
    if ar_words == 0:
        return "en"
    return "mixed"
