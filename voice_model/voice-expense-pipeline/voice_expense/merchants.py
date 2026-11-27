"""Merchant detection: gazetteer (exact + fuzzy) and a preposition pattern.

WHY a gazetteer (a list of known shops with aliases):
    Whisper writes brand names in either script ("Uber" or "أوبر"), people
    use Franco ("ober"), and some brands are normal words ("we", "total",
    "orange", "طلبات"). A curated list with aliases handles all of these and
    always returns ONE canonical name (e.g. "Uber"), which keeps reports and
    budgets clean.

Matching order (stop at the first that works):
    1. exact alias match on normalized tokens (multi-word aliases first);
       ambiguous aliases need a preposition before them or a context word;
    2. fuzzy match (similarity >= 88) for typos, only words of 3+ letters
       that are not common words;
    3. a pattern after a preposition (في/من/عند/at/from...) for shops that are
       not in the list. This has lower confidence and is flagged for review.
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from . import fuzzy
from .config import DATA_DIR
from .normalize import PREPOSITION_PREFIXES, Token, fold_phrase, prefix_variants

# Words that introduce a place/merchant ("at Cilantro", "من كارفور").
PREPOSITIONS = {
    "في", "ف", "من", "عند", "على", "علي", "ل", "لـ", "مع", "عن", "طريق",
    "at", "from", "in", "on", "to", "via", "through", "for", "with", "inside",
    "f", "fi", "fe", "men", "mn", "3and", "3nd", "3ala", "3la", "l", "le", "mel",
}
PATTERN_PREPOSITIONS = {"في", "ف", "من", "عند", "at", "from", "in", "on", "f", "fi", "fe", "men", "mn", "3and", "3nd", "mel"}

# Function words and very common words: never a merchant, never part of a note.
STOPWORDS = {
    # Arabic
    "في", "ف", "من", "عند", "على", "علي", "عن", "مع", "ب", "ل", "و", "او", "انا", "احنا", "هو", "هي",
    "ده", "دي", "دا", "دول", "اللي", "الي", "كان", "كانت", "عشان", "علشان", "لما", "بس", "كمان",
    "حوالي", "تقريبا", "يعني", "ايه", "شويه", "ما", "لا", "مش", "اني", "انه", "ان", "لي", "ليا", "لينا",
    "له", "لها", "بتاع", "بتاعت", "بتوع", "حق", "النهارده", "تمن", "ثمن", "حساب", "الحساب", "فلوس",
    "مبلغ", "بمبلغ", "بسعر", "سعر", "قيمه", "بقيمه", "عملت", "خدت", "اخدت", "كده", "برضه", "طيب",
    "اول", "تاني", "عليا", "علينا", "منها", "منه", "فيها", "فيه", "هناك", "هنا", "الاسبوع", "الشهر",
    "يوم", "ساعه", "الساعه", "فات", "الماضي", "واحد", "واحده", "صاحبي", "صاحبتي",
    # English
    "i", "we", "my", "the", "a", "an", "at", "for", "on", "in", "from", "to", "with", "of", "and",
    "this", "that", "it", "was", "is", "me", "our", "some", "about", "around", "just", "got", "today",
    "yesterday", "by", "via", "using", "its", "it's", "their", "his", "her", "total", "worth", "cost",
    "costs", "price", "amount", "spent", "paid", "bought", "pay", "spend", "buy", "ordered", "order",
    "had", "have", "has", "did", "do", "new", "few", "be", "been", "were", "are", "you", "your", "they",
    "there", "here", "then", "than", "so", "too", "also", "only", "again", "last", "ago", "after",
    "before", "into", "out", "up", "off", "over", "under", "like", "get", "gave", "give", "took",
    # Franco
    "ana", "f", "fi", "fe", "men", "mn", "3la", "3ala", "el", "w", "b", "bel", "bl", "da", "di", "elly",
    "eli", "3ashan", "3shan", "le", "l", "mel",
}
GENERIC_PLACES = {
    "محل", "المحل", "السوق", "سوق", "البيت", "بيت", "الشغل", "شغل", "المكتب", "مكتب", "الجامعه",
    "الكليه", "الشارع", "شارع", "المول", "مول", "الكشك", "مكان", "حته", "الحته", "البلد", "وسط",
    "store", "shop", "home", "work", "office", "market", "mall", "place", "street", "kiosk",
    "restaurant", "cafe", "supermarket", "town", "downtown", "city", "online", "app", "website",
    "ma7al", "elma7al", "beit", "elbeit", "sho3'l", "shoghl", "friend", "friends", "mom", "dad",
    "mother", "father", "brother", "sister", "family", "kids", "wife", "husband", "colleague",
    "اصحابي", "صحابي", "ماما", "بابا", "اخويا", "اختي", "مراتي", "جوزي", "العيال", "الولاد",
}


@dataclass
class Merchant:
    name: str
    category: str
    aliases: list[str]
    ambiguous_aliases: list[str] = field(default_factory=list)
    context: set[str] = field(default_factory=set)
    strict: bool = False
    strict_prepositions: set[str] = field(default_factory=set)


@dataclass
class MerchantMatch:
    name: str
    category: Optional[str]
    start: int
    end: int
    confidence: float
    method: str  # "exact" | "exact_ambiguous" | "fuzzy" | "pattern"
    text: str

    @property
    def in_gazetteer(self) -> bool:
        return self.method != "pattern"

    @property
    def token_indices(self) -> set[int]:
        return set(range(self.start, self.end))


class Gazetteer:
    """Loads data/merchants.json and answers "which merchant is in these tokens?"."""

    def __init__(self, path: Optional[Path] = None) -> None:
        p = path or (DATA_DIR / "merchants.json")
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        self.merchants: list[Merchant] = []
        self.index: dict[tuple[str, ...], tuple[Merchant, bool]] = {}
        self.max_len = 1
        for m in data["merchants"]:
            merchant = Merchant(
                name=m["name"],
                category=m.get("category", "other"),
                aliases=list(m.get("aliases", [])),
                ambiguous_aliases=list(m.get("ambiguous_aliases", [])),
                context={k for c in m.get("context", []) for k in fold_phrase(c)},
                strict=bool(m.get("strict", False)),
                strict_prepositions={k for c in m.get("strict_prepositions", []) for k in fold_phrase(c)},
            )
            self.merchants.append(merchant)
            ambiguous_keys = {fold_phrase(a) for a in merchant.ambiguous_aliases}
            names = [] if fold_phrase(merchant.name) in ambiguous_keys else [merchant.name]
            for alias in merchant.aliases + names:
                key = fold_phrase(alias)
                if key:
                    self.index.setdefault(key, (merchant, False))
                    self.max_len = max(self.max_len, len(key))
            for alias in merchant.ambiguous_aliases:
                key = fold_phrase(alias)
                if key:
                    self.index.setdefault(key, (merchant, True))
                    self.max_len = max(self.max_len, len(key))
        # Single-token, non-ambiguous aliases for fuzzy matching (by script).
        self.fuzzy_aliases: list[tuple[str, Merchant]] = [
            (" ".join(k), mm) for k, (mm, amb) in self.index.items() if not amb and len(" ".join(k)) >= 4
        ]

    def __len__(self) -> int:
        return len(self.merchants)

    def by_name(self, name: str) -> Optional[Merchant]:
        for m in self.merchants:
            if m.name.lower() == name.lower():
                return m
        return None

    def canonical(self, raw: Optional[str]) -> Optional[str]:
        """Map any alias/variant to the canonical name (used by evaluation)."""
        if not raw:
            return None
        key = fold_phrase(raw)
        hit = self.index.get(key)
        if hit:
            return hit[0].name
        m = self.by_name(raw)
        return m.name if m else None

    # --------------------------------------------------------------------- exact
    def _ambiguous_ok(self, m: Merchant, tokens: list[Token], i: int, end: int, prefix: str,
                      proper_nouns: Optional[set[str]] = None) -> tuple[bool, float]:
        prev = tokens[i - 1].fold if i > 0 else ""
        nxt = tokens[end].fold if end < len(tokens) else ""
        if m.strict:
            preps = m.strict_prepositions
            if prefix and prefix in PREPOSITION_PREFIXES and preps:
                return True, 0.8
            if prev in preps:
                return True, 0.8
            neighbors = {prev, nxt}
            if neighbors & m.context:
                return True, 0.85
            # A capitalised brand in the middle of a sentence ("gas at Total") after a preposition.
            if proper_nouns and tokens[i].fold in proper_nouns and prev in PREPOSITIONS:
                return True, 0.75
            return False, 0.0
        if prefix and prefix in PREPOSITION_PREFIXES:
            return True, 0.8
        if prev in PREPOSITIONS:
            return True, 0.8
        window = {t.fold for t in tokens[max(0, i - 3) : min(len(tokens), end + 3)]}
        window |= {rest for t in tokens[max(0, i - 3) : min(len(tokens), end + 3)] for _, rest in prefix_variants(t.fold)}
        if window & m.context:
            return True, 0.85
        return False, 0.0

    def find_exact(self, tokens: list[Token], skip: Optional[set[int]] = None,
                   original_text: str = "") -> list[MerchantMatch]:
        skip = skip or set()
        proper_nouns = _midsentence_capitalized(original_text)
        out: list[MerchantMatch] = []
        i = 0
        n = len(tokens)
        while i < n:
            if i in skip:
                i += 1
                continue
            hit: Optional[MerchantMatch] = None
            for length in range(min(self.max_len, n - i), 0, -1):
                if any(k in skip for k in range(i, i + length)):
                    continue
                rest = tuple(t.fold for t in tokens[i + 1 : i + length])
                for prefix, first in prefix_variants(tokens[i].fold):
                    entry = self.index.get((first,) + rest)
                    if entry is None:
                        continue
                    merchant, ambiguous = entry
                    if ambiguous:
                        ok, conf = self._ambiguous_ok(merchant, tokens, i, i + length, prefix, proper_nouns)
                        if not ok:
                            continue
                        method = "exact_ambiguous"
                    else:
                        conf, method = 0.95, "exact"
                    hit = MerchantMatch(merchant.name, merchant.category, i, i + length, conf, method,
                                        " ".join(t.text for t in tokens[i : i + length]))
                    break
                if hit:
                    break
            if hit:
                out.append(hit)
                i = hit.end
            else:
                i += 1
        return out

    # --------------------------------------------------------------------- fuzzy
    def find_fuzzy(self, tokens: list[Token], skip: Optional[set[int]] = None,
                   blocked: Optional[set[str]] = None, threshold: float = 88.0) -> Optional[MerchantMatch]:
        skip = skip or set()
        blocked = blocked or set()
        best: Optional[MerchantMatch] = None
        best_score = 0.0
        for tok in tokens:
            if tok.index in skip or tok.is_number:
                continue
            for _, word in prefix_variants(tok.fold):
                if len(word) < 3 or word in blocked or word in STOPWORDS or word in GENERIC_PLACES:
                    continue
                if any(ch.isdigit() for ch in word) and not tok.is_latin:
                    continue
                is_ar = bool(re.match(r"[؀-ۿ]", word))
                for alias, m in self.fuzzy_aliases:
                    if " " in alias:
                        continue
                    if is_ar != bool(re.match(r"[؀-ۿ]", alias)):
                        continue
                    if abs(len(alias) - len(word)) > 3:
                        continue
                    score = fuzzy.ratio(word, alias)
                    if score >= threshold and score > best_score:
                        best_score = score
                        best = MerchantMatch(m.name, m.category, tok.index, tok.index + 1, 0.7, "fuzzy", tok.text)
        return best

    # ------------------------------------------------------------------- pattern
    def find_pattern(self, tokens: list[Token], skip: Optional[set[int]] = None,
                     blocked: Optional[set[str]] = None, original_text: str = "") -> Optional[MerchantMatch]:
        """Shop name after a preposition, for shops not in the gazetteer."""
        from .numbers import is_number_word

        skip = skip or set()
        blocked = blocked or set()
        n = len(tokens)

        def usable(k: int, span_start: Optional[int] = None) -> bool:
            if k >= n or k in skip:
                return False
            t = tokens[k]
            # A number may end a Latin name ("Route 66") but never start one.
            if t.is_number:
                return (span_start is not None and k > span_start and tokens[k - 1].is_latin
                        and re.fullmatch(r"\d{1,4}", t.text) is not None)
            if len(t.fold) < 2 or not any(ch.isalpha() for ch in t.fold):
                return False
            for _, v in prefix_variants(t.fold):
                if v in STOPWORDS or v in blocked or v in GENERIC_PLACES or is_number_word(v):
                    return False
            return True

        for i, tok in enumerate(tokens):
            if i in skip:
                continue
            start: Optional[int] = None
            if tok.fold in PATTERN_PREPOSITIONS:
                start = i + 1
                while start < n and start not in skip and tokens[start].fold in ("the", "a", "el", "ال"):
                    start += 1
            if start is None or not usable(start):
                continue
            end = start
            while end < n and end - start < 3 and usable(end, start):
                end += 1
                if tokens[end - 1].is_number:
                    break
            span_tokens = tokens[start:end]
            # Arabic words after "في" are usually common nouns; require that a Latin proper
            # noun is present, or that the preposition is "عند"/"من" (people/shops).
            if all(t.is_arabic for t in span_tokens) and tok.fold not in ("عند", "من", "3and", "3nd", "men", "mn"):
                continue
            text = " ".join(t.text for t in span_tokens)
            display = _restore_case(text, original_text)
            return MerchantMatch(display, None, start, end, 0.5, "pattern", text)
        return None


def _midsentence_capitalized(text: str) -> set[str]:
    """Lower-cased Latin words written with a capital letter that are not the first word of a sentence."""
    out: set[str] = set()
    if not text:
        return out
    for sentence in re.split(r"[.!?؟\n]+", text):
        words = re.findall(r"[A-Za-z][A-Za-z&'.+]*", sentence)
        first_latin_at_start = bool(re.match(r"\s*[A-Za-z]", sentence))
        for k, w in enumerate(words):
            if k == 0 and first_latin_at_start:
                continue
            if w[0].isupper():
                out.add(w.lower().rstrip("."))
    return out


def _restore_case(span: str, original: str) -> str:
    """Find `span` in the original transcript (case-insensitive) to keep the user's casing."""
    if not original or not re.search(r"[a-z]", span):
        return span
    m = re.search(re.escape(span), original, flags=re.IGNORECASE)
    if m:
        found = m.group(0)
        return found if any(ch.isupper() for ch in found) else found.title()
    return span.title()


@lru_cache(maxsize=1)
def get_gazetteer() -> Gazetteer:
    return Gazetteer()


def merchant_names() -> list[str]:
    return [m.name for m in get_gazetteer().merchants]
