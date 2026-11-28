"""Category classification from bilingual keywords + the merchant's default category.

WHY this decision order (explicit keyword > merchant default > LLM > other):
    The words the user actually says are the best evidence. "دفعت 500 في كارفور
    على هدوم" is clothes bought at Carrefour, so it is `shopping`, even though
    Carrefour's default is `groceries`. When no category word is said, the
    merchant tells us a lot (Uber -> transport). The LLM is only a guess, and
    "other" is the last resort. Each step down lowers the confidence.

Keywords come from data/categories.json so non-programmers can add words.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

from .config import DATA_DIR
from .normalize import Token, fold_phrase, prefix_variants


@dataclass
class CategoryInfo:
    id: str
    en: str
    ar: str
    priority: int
    keywords: list[str]


@dataclass
class KeywordHit:
    category: str
    start: int
    end: int
    weight: int
    text: str


@dataclass
class CategoryResult:
    category: str
    confidence: float
    source: str  # "keyword" | "keyword+merchant" | "merchant" | "llm" | "other"
    candidates: list[dict] = field(default_factory=list)
    consumed: set[int] = field(default_factory=set)
    hits: list[KeywordHit] = field(default_factory=list)


@lru_cache(maxsize=4)
def load_categories(path: Optional[str] = None) -> tuple[CategoryInfo, ...]:
    p = Path(path) if path else DATA_DIR / "categories.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    return tuple(
        CategoryInfo(id=c["id"], en=c["en"], ar=c["ar"], priority=int(c.get("priority", 0)), keywords=list(c["keywords"]))
        for c in data["categories"]
    )


def category_ids() -> list[str]:
    return [c.id for c in load_categories()]


def category_labels() -> dict[str, str]:
    """id -> "English / Arabic" label (used by the UI)."""
    return {c.id: f"{c.en} / {c.ar}" for c in load_categories()}


@lru_cache(maxsize=1)
def _index() -> tuple[dict[tuple[str, ...], str], int, dict[str, int]]:
    idx: dict[tuple[str, ...], str] = {}
    priorities: dict[str, int] = {}
    max_len = 1
    for c in load_categories():
        priorities[c.id] = c.priority
        for kw in c.keywords:
            key = fold_phrase(kw)
            if not key:
                continue
            # First category that lists a keyword owns it (keeps results stable).
            idx.setdefault(key, c.id)
            max_len = max(max_len, len(key))
    return idx, max_len, priorities


def keyword_folds() -> set[str]:
    """All single-word keyword keys (used by merchants.py to avoid treating 'groceries' as a shop)."""
    idx, _, _ = _index()
    out: set[str] = set()
    for key in idx:
        out.update(key)
    return out


def find_keywords(tokens: list[Token], skip: Optional[set[int]] = None) -> list[KeywordHit]:
    """Longest-match keyword search. The first word may carry a prefix (بالفيزا, للدكتور)."""
    idx, max_len, _ = _index()
    skip = skip or set()
    hits: list[KeywordHit] = []
    i = 0
    n = len(tokens)
    while i < n:
        if i in skip:
            i += 1
            continue
        found = False
        for length in range(min(max_len, n - i), 0, -1):
            if any(k in skip for k in range(i, i + length)):
                continue
            rest = tuple(t.fold for t in tokens[i + 1 : i + length])
            for _, first in prefix_variants(tokens[i].fold):
                cat = idx.get((first,) + rest)
                if cat:
                    hits.append(KeywordHit(cat, i, i + length, 2 if length > 1 else 1,
                                           " ".join(t.text for t in tokens[i : i + length])))
                    i += length
                    found = True
                    break
            if found:
                break
        if not found:
            i += 1
    return hits


def classify(
    tokens: list[Token],
    skip: Optional[set[int]] = None,
    merchant_category: Optional[str] = None,
    merchant_confidence: float = 0.0,
    llm_category: Optional[str] = None,
) -> CategoryResult:
    """Pick a category following the documented precedence. Returns top-2 candidates too."""
    _, _, priorities = _index()
    hits = find_keywords(tokens, skip)
    scores: dict[str, float] = {}
    for h in hits:
        if h.category == "income":
            continue  # income is decided by transaction_type, not by a keyword alone
        scores[h.category] = scores.get(h.category, 0.0) + h.weight
    strong = {c: s for c, s in scores.items() if c != "other"}
    ranked = sorted(strong.items(), key=lambda kv: (-kv[1], -priorities.get(kv[0], 0)))
    candidates: list[dict] = [{"category": c, "score": s, "source": "keyword"} for c, s in ranked]
    if merchant_category and merchant_category not in strong:
        candidates.append({"category": merchant_category, "score": 0.5, "source": "merchant"})
    if llm_category and all(c["category"] != llm_category for c in candidates):
        candidates.append({"category": llm_category, "score": 0.3, "source": "llm"})
    consumed = {k for h in hits for k in range(h.start, h.end)}

    if ranked:
        best, best_score = ranked[0]
        conf = 0.85
        source = "keyword"
        if merchant_category == best:
            conf = 0.92
            source = "keyword+merchant"
        if len(ranked) > 1 and ranked[1][1] == best_score:
            conf = min(conf, 0.65)  # tie broken only by priority
        return CategoryResult(best, conf, source, candidates[:2], consumed, hits)
    if merchant_category:
        conf = 0.75 if merchant_confidence >= 0.8 else 0.65
        return CategoryResult(merchant_category, conf, "merchant", candidates[:2], consumed, hits)
    if llm_category:
        return CategoryResult(llm_category, 0.6, "llm", candidates[:2], consumed, hits)
    if "other" in scores:
        return CategoryResult("other", 0.5, "keyword", [{"category": "other", "score": scores["other"], "source": "keyword"}], consumed, hits)
    return CategoryResult("other", 0.3, "other", candidates[:2], consumed, hits)
