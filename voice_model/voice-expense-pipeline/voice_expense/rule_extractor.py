"""The offline, deterministic baseline: combine all rule modules into one result.

WHY rules first:
    Rules are free, instant, private (nothing leaves the phone/server) and
    always give the same answer, which makes them easy to test. The optional
    LLM is only asked for help when the rules are unsure (hybrid mode).

Order of work (each step marks the tokens it used so later steps ignore them):
    currency -> payment method -> date/time -> merchant (gazetteer)
    -> amount -> merchant (pattern) -> category -> transaction type -> note
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Optional

from .categories import classify, keyword_folds
from .currency import detect_currency
from .dates import MONTHS, TIME_OF_DAY, TODAY_WORDS, WEEKDAYS, YESTERDAY_WORDS, parse_datetime
from .merchants import STOPWORDS, get_gazetteer
from .normalize import Token, detect_language, fold_phrase, normalize_text, prefix_variants, tokenize
from .numbers import INCOME_VERBS, PAY_VERBS, find_numbers, is_number_word, select_amount

# --- payment method vocabulary (folded) -------------------------------------
_PAYMENT_PHRASES: list[tuple[str, str, bool]] = [
    # (phrase, method, needs_context) - generic words like "card"/"wallet" need "by/with/ب..."
    ("فودافون كاش", "wallet", False), ("vodafone cash", "wallet", False), ("اتصالات كاش", "wallet", False),
    ("etisalat cash", "wallet", False), ("اورانج كاش", "wallet", False), ("orange cash", "wallet", False),
    ("orange money", "wallet", False), ("we pay", "wallet", False), ("وي باي", "wallet", False),
    ("انستا باي", "wallet", False), ("انستاباي", "wallet", False), ("instapay", "wallet", False),
    ("insta pay", "wallet", False), ("e-wallet", "wallet", False), ("محفظه الكترونيه", "wallet", False),
    ("محفظه", "wallet", True), ("wallet", "wallet", True), ("ma7faza", "wallet", True),
    ("credit card", "card", False), ("debit card", "card", False), ("كريديت كارد", "card", False),
    ("apple pay", "card", False), ("google pay", "card", False), ("فيزا", "card", False),
    ("visa", "card", False), ("ماستر كارد", "card", False), ("ماستركارد", "card", False),
    ("mastercard", "card", False), ("ميزه", "card", False), ("meeza", "card", False),
    ("كريديت", "card", False), ("ديبت", "card", False), ("كارت", "card", True), ("الكارت", "card", True),
    ("card", "card", True), ("kart", "card", True), ("فيزه", "card", False),
    ("كاش", "cash", False), ("نقدي", "cash", False), ("نقدا", "cash", False), ("cash", "cash", False),
    ("kash", "cash", False), ("ka4", "cash", False), ("in cash", "cash", False),
]
_PAY_CONTEXT_BEFORE = {"by", "with", "via", "using", "on", "from", "through", "my", "ب", "من", "عن", "بال",
                       "b", "bel", "bl", "paid", "دفعت", "حاسبت", "el"}
_NOT_PAYMENT_AFTER = {"شحن", "الشحن", "الكهربا", "كهربا", "recharge", "top", "gift", "هديه"}
_NOT_PAYMENT_BEFORE = {"gift", "recharge", "scratch", "شحن", "هديه", "اشتريت", "bought", "new", "جديده"}

# Income: strong verbs vs salary-like nouns (a pay verb + salary = paying someone's salary).
_INCOME_STRONG = {"قبضت", "اتحولي", "حولولي", "اتحولتلي", "استلمت", "كسبت", "received", "earned",
                  "2abadt", "et7awelly", "estalamt", "receive"}
_INCOME_PHRASES = [("got", "paid"), ("جالي", "تحويل"), ("وصلني", "تحويل"), ("وصلني", "المرتب"),
                   ("نزل", "المرتب"), ("نزلي", "المرتب")]
_INCOME_NOUNS = {"مرتب", "المرتب", "مرتبي", "راتب", "salary", "paycheck", "bonus", "بونص", "مكافاه",
                 "income", "freelance", "commission", "عموله", "mortab", "rateb"}

_PAYMENT_INDEX: dict[tuple[str, ...], tuple[str, bool]] = {}


def _payment_index() -> dict[tuple[str, ...], tuple[str, bool]]:
    if not _PAYMENT_INDEX:
        for phrase, method, needs in _PAYMENT_PHRASES:
            _PAYMENT_INDEX.setdefault(fold_phrase(phrase), (method, needs))
    return _PAYMENT_INDEX


@dataclass
class RuleExtraction:
    """Everything the rules found, before it becomes an ExpenseDraft."""

    fields: dict[str, Any]
    confidence: dict[str, float]
    needs_review: list[str]
    normalized_text: str
    language: str
    category_candidates: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)


def detect_payment(tokens: list[Token], skip: set[int]) -> tuple[str, float, set[int]]:
    """Return (method, confidence, consumed token indices)."""
    idx = _payment_index()
    max_len = max(len(k) for k in idx)
    n = len(tokens)
    for i in range(n):
        if i in skip:
            continue
        for length in range(min(max_len, n - i), 0, -1):
            if any(k in skip for k in range(i, i + length)):
                continue
            rest = tuple(t.fold for t in tokens[i + 1 : i + length])
            for prefix, first in prefix_variants(tokens[i].fold):
                entry = idx.get((first,) + rest)
                if entry is None:
                    continue
                method, needs_context = entry
                prev = tokens[i - 1].fold if i > 0 else ""
                nxt = tokens[i + length].fold if i + length < n else ""
                if nxt in _NOT_PAYMENT_AFTER or prev in _NOT_PAYMENT_BEFORE:
                    continue
                if needs_context:
                    prev2 = tokens[i - 2].fold if i > 1 else ""
                    if not (prefix.startswith("ب") or prev in _PAY_CONTEXT_BEFORE
                            or (prev in ("my", "el") and prev2 in _PAY_CONTEXT_BEFORE)):
                        continue
                consumed = set(range(i, i + length))
                # Also swallow the little words before it ("by card", "in cash", "with my card").
                if prev in {"by", "with", "via", "using", "in", "on", "b", "bel", "bl"} and (i - 1) not in skip:
                    consumed.add(i - 1)
                elif prev == "my" and (i - 1) not in skip:
                    consumed.add(i - 1)
                    if i > 1 and tokens[i - 2].fold in _PAY_CONTEXT_BEFORE:
                        consumed.add(i - 2)
                return method, 0.9, consumed
    return "unknown", 0.6, set()


def detect_transaction_type(tokens: list[Token]) -> tuple[str, float, set[int]]:
    folds = [t.fold for t in tokens]
    for i in range(len(folds)):
        for seq in _INCOME_PHRASES:
            if tuple(folds[i : i + len(seq)]) == seq:
                return "income", 0.9, set(range(i, i + len(seq)))
    for i, f in enumerate(folds):
        if f in _INCOME_STRONG:
            return "income", 0.9, {i}
    has_pay = any(f in PAY_VERBS for f in folds)
    for f in folds:
        variants = {v for _, v in prefix_variants(f)}
        if variants & _INCOME_NOUNS and not has_pay:
            return "income", 0.75, set()
    return "expense", 0.9 if has_pay else 0.8, set()


def _date_word_folds() -> set[str]:
    out = set(TODAY_WORDS) | set(YESTERDAY_WORDS) | set(WEEKDAYS) | set(MONTHS) | set(TIME_OF_DAY)
    return out


def extract_rules(text: str, now: datetime, default_currency: str = "EGP",
                  review_threshold: float = 0.6) -> RuleExtraction:
    """Run every rule module on `text` and return fields + confidences + review flags."""
    normalized = normalize_text(text or "")
    tokens = tokenize(normalized)
    language = detect_language(text or "")
    warnings: list[str] = []
    debug: dict[str, Any] = {}

    if not tokens:
        return RuleExtraction(
            fields={
                "transaction_type": "expense", "amount": None, "currency": default_currency, "merchant": None,
                "category": "other", "date": now.date(), "time": None, "payment_method": "unknown", "note": None,
            },
            confidence={k: 0.0 for k in ("transaction_type", "amount", "currency", "merchant", "category",
                                         "date", "time", "payment_method", "note")},
            needs_review=["amount", "currency", "merchant", "category", "date", "time", "payment_method"],
            normalized_text=normalized,
            language=language,
            warnings=["Empty transcript: nothing to extract. Please type or record the expense again."],
        )

    # 1. currency
    currency, cur_conf, cur_spans = detect_currency(tokens, default_currency)
    cur_idx = {k for s in cur_spans for k in range(s.start, s.end)}
    # 2. payment method
    payment, pay_conf, pay_idx = detect_payment(tokens, cur_idx)
    # 3. date / time
    dt = parse_datetime(tokens, now, skip=cur_idx | pay_idx)
    date_idx = dt.consumed
    # 4. merchant (gazetteer, exact)
    gaz = get_gazetteer()
    used = cur_idx | pay_idx | date_idx
    exact = gaz.find_exact(tokens, skip=used, original_text=text or "")
    merchant_match = None
    if exact:
        exact.sort(key=lambda m: (-m.confidence, -(m.end - m.start), m.start))
        merchant_match = exact[0]
    # 5. amount (merchant names like "19011" or "7 Up" are skipped)
    merch_idx_all = {k for m in exact for k in range(m.start, m.end)}
    spans = find_numbers(tokens, skip=used | merch_idx_all)
    amount_res = select_amount(tokens, spans, [(s.start, s.end, s.code) for s in cur_spans], dt.month_indices,
                               date_idx)
    amount_idx = amount_res.consumed
    # currency right next to the chosen amount wins when several are present
    if amount_res.currency_span_index is not None:
        for s in cur_spans:
            if s.start == amount_res.currency_span_index:
                currency = s.code
                cur_conf = 0.95 if len({c.code for c in cur_spans}) == 1 else 0.8
    blocked = keyword_folds() | _date_word_folds() | PAY_VERBS | INCOME_VERBS
    # 6. merchant fuzzy / pattern
    if merchant_match is None:
        merchant_match = gaz.find_fuzzy(tokens, skip=used | amount_idx, blocked=blocked)
    if merchant_match is None:
        merchant_match = gaz.find_pattern(tokens, skip=used | amount_idx, blocked=blocked, original_text=text)
    merchant_idx = merchant_match.token_indices if merchant_match else set()
    # 7. category
    cat = classify(tokens, skip=used | amount_idx | merchant_idx,
                   merchant_category=merchant_match.category if merchant_match else None,
                   merchant_confidence=merchant_match.confidence if merchant_match else 0.0)
    # 8. transaction type
    tx_type, tx_conf, tx_idx = detect_transaction_type(tokens)
    category, cat_conf = cat.category, cat.confidence
    if tx_type == "income":
        category, cat_conf = "income", 0.9

    # 9. note: leftover descriptive words
    all_used = used | amount_idx | merchant_idx | tx_idx | {k for sp in spans for k in range(sp.start, sp.end)}
    note_words: list[str] = []
    for t in tokens:
        if t.index in all_used:
            continue
        variants = [v for _, v in prefix_variants(t.fold)]
        if any(v in STOPWORDS or v in PAY_VERBS or v in INCOME_VERBS for v in variants):
            continue
        if t.fold in ("$", "€", "£") or is_number_word(t.fold) or t.is_number:
            continue
        word = t.text
        # Drop an attached preposition from a category word: "للدكتور" -> "دكتور".
        for prefix, rest in prefix_variants(t.fold):
            if prefix in ("ل", "لل", "ب", "بال", "ف", "فال", "و", "وال") and rest in keyword_folds():
                word = rest
                break
        note_words.append(word)
    note = " ".join(note_words[:8]) or None

    amount: Optional[Decimal] = amount_res.value
    merchant_name = merchant_match.name if merchant_match else None
    merchant_conf = merchant_match.confidence if merchant_match else 0.6

    fields = {
        "transaction_type": tx_type,
        "amount": amount,
        "currency": currency,
        "merchant": merchant_name,
        "category": category,
        "date": dt.date,
        "time": dt.time,
        "payment_method": payment,
        "note": note,
    }
    confidence = {
        "transaction_type": round(tx_conf, 2),
        "amount": round(amount_res.confidence, 2),
        "currency": round(cur_conf, 2),
        "merchant": round(merchant_conf, 2),
        "category": round(cat_conf, 2),
        "date": round(dt.date_confidence, 2),
        "time": round(dt.time_confidence, 2) if dt.time else 0.0,
        "payment_method": round(pay_conf, 2),
        "note": 0.6 if note else 0.0,
    }
    review: list[str] = []
    if amount is None:
        review.append("amount")
        warnings.append("No amount found.")
    elif amount_res.ambiguous or amount_res.confidence < review_threshold:
        review.append("amount")
    if cur_conf < review_threshold:
        review.append("currency")
    if merchant_match is not None and (merchant_match.method == "pattern" or merchant_conf < review_threshold):
        review.append("merchant")
    if cat_conf < review_threshold:
        review.append("category")
    if dt.date_review or dt.date_confidence < review_threshold:
        review.append("date")
    if dt.time and dt.time_review:
        review.append("time")
    if tx_conf < review_threshold:
        review.append("transaction_type")
    for note_msg in dt.notes:
        warnings.append(f"Date: {note_msg}")

    debug.update({
        "amount_reason": amount_res.reason,
        "amount_candidates": [(str(v), s) for v, s in amount_res.candidates],
        "merchant_method": merchant_match.method if merchant_match else None,
        "category_source": cat.source,
        "date_source": dt.date_source,
        "tokens": [t.text for t in tokens],
    })
    return RuleExtraction(
        fields=fields,
        confidence=confidence,
        needs_review=review,
        normalized_text=normalized,
        language=language,
        category_candidates=cat.candidates,
        warnings=warnings,
        debug=debug,
    )
