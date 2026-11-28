"""Fuzzy string similarity (0-100) with a pure-Python fallback.

WHY: rapidfuzz is fast and is listed in requirements.txt, but the project must
never crash if a package is missing. When rapidfuzz is not installed we use a
small pure-Python version of the SAME formulas (normalized Indel similarity,
i.e. 2 * longest-common-subsequence / total length), so results do not change
depending on whether rapidfuzz is installed. It is just slower.
"""
from __future__ import annotations

try:  # pragma: no cover - depends on the environment
    from rapidfuzz import fuzz as _rf_fuzz

    HAVE_RAPIDFUZZ = True
except Exception:  # pragma: no cover
    _rf_fuzz = None
    HAVE_RAPIDFUZZ = False


def _lcs_len(a: str, b: str) -> int:
    if len(a) < len(b):
        a, b = b, a
    prev = [0] * (len(b) + 1)
    for ch in a:
        cur = [0]
        for j, ch2 in enumerate(b, 1):
            cur.append(prev[j - 1] + 1 if ch == ch2 else max(prev[j], cur[j - 1]))
        prev = cur
    return prev[-1]


def _py_ratio(a: str, b: str) -> float:
    if not a and not b:
        return 100.0
    if not a or not b:
        return 0.0
    return 100.0 * 2 * _lcs_len(a, b) / (len(a) + len(b))


def ratio(a: str, b: str) -> float:
    """Similarity of two strings, 0 (different) to 100 (identical)."""
    if _rf_fuzz is not None:
        return float(_rf_fuzz.ratio(a, b))
    return _py_ratio(a, b)


def token_set_ratio(a: str, b: str) -> float:
    """Word-order-insensitive similarity ("Cafe Zooba" vs "zooba cafe" -> 100)."""
    if _rf_fuzz is not None:
        return float(_rf_fuzz.token_set_ratio(a, b))
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    inter = sa & sb
    diff_a, diff_b = sa - sb, sb - sa
    if inter and (not diff_a or not diff_b):
        return 100.0
    s_inter = " ".join(sorted(inter))
    s_a = " ".join(sorted(diff_a))
    s_b = " ".join(sorted(diff_b))
    combined_a = (s_inter + " " + s_a).strip()
    combined_b = (s_inter + " " + s_b).strip()
    scores = [_py_ratio(combined_a, combined_b)]
    if s_inter:
        scores.append(_py_ratio(s_inter, combined_a))
        scores.append(_py_ratio(s_inter, combined_b))
    return max(scores)
