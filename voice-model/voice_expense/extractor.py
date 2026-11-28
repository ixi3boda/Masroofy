"""Choose between rules, LLM and hybrid extraction, and merge results field by field.

WHY hybrid is the default:
    Rules are right most of the time and cost nothing. The LLM is called only
    when the rules are missing something (no amount) or unsure (a confidence
    below HYBRID_CONFIDENCE_THRESHOLD). Then, for each field:
      * rule value missing or low-confidence -> take the LLM value;
      * rule value confident -> keep it (an LLM agreeing raises confidence);
    `field_sources` records who won each field, which is useful when debugging.
If anything goes wrong with the LLM, the rule result is returned with a warning.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Optional

from .config import Settings, get_settings
from .llm_extractor import LLMError, LLMExtractor, LLMOutput, LLMUnavailable
from .merchants import get_gazetteer
from .rule_extractor import RuleExtraction, extract_rules

FIELDS = ("transaction_type", "amount", "currency", "merchant", "category", "date", "time", "payment_method", "note")
# Fields whose low confidence triggers an LLM call in hybrid mode.
TRIGGER_FIELDS = ("amount", "category", "date", "merchant", "currency")


@dataclass
class ExtractionOutcome:
    fields: dict[str, Any]
    confidence: dict[str, float]
    needs_review: list[str]
    method: str
    normalized_text: str
    language: str
    warnings: list[str] = field(default_factory=list)
    field_sources: dict[str, str] = field(default_factory=dict)
    category_candidates: list[dict] = field(default_factory=list)
    debug: dict[str, Any] = field(default_factory=dict)


_llm_singleton: Optional[LLMExtractor] = None


def get_llm(settings: Settings) -> LLMExtractor:
    """Create the LLM extractor once per process (clients are reused)."""
    global _llm_singleton
    if _llm_singleton is None or _llm_singleton.settings is not settings:
        _llm_singleton = LLMExtractor(settings)
    return _llm_singleton


def _llm_fields(out: LLMOutput, now: datetime) -> dict[str, Any]:
    gaz = get_gazetteer()
    merchant = out.merchant
    if merchant:
        merchant = gaz.canonical(merchant) or merchant
    return {
        "transaction_type": out.transaction_type,
        "amount": Decimal(str(out.amount)) if out.amount is not None else None,
        "currency": out.currency,
        "merchant": merchant,
        "category": out.category,
        "date": date.fromisoformat(out.date) if out.date else now.date(),
        "time": out.time,
        "payment_method": out.payment_method,
        "note": out.note,
    }


def _same(a: Any, b: Any) -> bool:
    if isinstance(a, Decimal) or isinstance(b, Decimal):
        try:
            return a is not None and b is not None and abs(Decimal(str(a)) - Decimal(str(b))) < Decimal("0.01")
        except Exception:
            return False
    if isinstance(a, str) and isinstance(b, str):
        return a.strip().lower() == b.strip().lower()
    return a == b


def _review_list(fields: dict[str, Any], conf: dict[str, float], threshold: float,
                 extra: set[str]) -> list[str]:
    review = set(extra)
    if fields.get("amount") is None:
        review.add("amount")
    for k in ("amount", "currency", "category", "date", "transaction_type"):
        if conf.get(k, 0.0) < threshold:
            review.add(k)
    if fields.get("merchant") is not None and conf.get("merchant", 0.0) < threshold:
        review.add("merchant")
    if fields.get("time") is not None and conf.get("time", 0.0) < 0.5:
        review.add("time")
    return [f for f in FIELDS if f in review]


def needs_llm(rules: RuleExtraction, threshold: float) -> list[str]:
    """Which fields make hybrid mode ask the LLM."""
    weak = []
    if rules.fields.get("amount") is None:
        weak.append("amount")
    for k in TRIGGER_FIELDS:
        if k == "merchant" and rules.fields.get("merchant") is None:
            continue
        if rules.confidence.get(k, 0.0) < threshold and k not in weak:
            weak.append(k)
    if rules.fields.get("category") == "other" and "category" not in weak:
        weak.append("category")
    return weak


def merge(rules: RuleExtraction, llm_fields: dict[str, Any], threshold: float) -> tuple[dict, dict, dict, set[str]]:
    """Field-by-field merge. Returns (fields, confidence, sources, extra_review)."""
    gaz = get_gazetteer()
    fields: dict[str, Any] = {}
    conf: dict[str, float] = {}
    sources: dict[str, str] = {}
    extra_review: set[str] = set()
    for k in FIELDS:
        rv = rules.fields.get(k)
        rc = rules.confidence.get(k, 0.0)
        lv = llm_fields.get(k)
        rule_weak = rv is None or rc < threshold or (k == "category" and rv == "other")
        if k == "merchant" and rv is None:
            rule_weak = True
        if rule_weak and lv is not None:
            fields[k] = lv
            conf[k] = 0.8 if _same(rv, lv) else 0.7
            sources[k] = "llm"
            if k == "merchant" and gaz.canonical(str(lv)) is None:
                extra_review.add("merchant")  # LLM merchant not in our list: let the user check it
        else:
            fields[k] = rv
            conf[k] = max(rc, 0.9) if (lv is not None and _same(rv, lv)) else rc
            sources[k] = "rules+llm" if (lv is not None and _same(rv, lv)) else "rules"
    if fields.get("transaction_type") == "income":
        fields["category"] = "income"
    return fields, conf, sources, extra_review


def extract(text: str, now: datetime, settings: Optional[Settings] = None, mode: Optional[str] = None,
            llm: Optional[LLMExtractor] = None) -> ExtractionOutcome:
    """Run the extractor in `mode` (rules | llm | hybrid). Never raises because of the LLM."""
    settings = settings or get_settings()
    mode = (mode or settings.extractor_mode or "hybrid").lower()
    if mode not in ("rules", "llm", "hybrid"):
        mode = "hybrid"
    rules = extract_rules(text, now, settings.default_currency, settings.review_confidence_threshold)
    warnings = list(rules.warnings)
    base = ExtractionOutcome(
        fields=dict(rules.fields),
        confidence=dict(rules.confidence),
        needs_review=list(rules.needs_review),
        method="rules",
        normalized_text=rules.normalized_text,
        language=rules.language,
        warnings=warnings,
        field_sources={k: "rules" for k in FIELDS},
        category_candidates=list(rules.category_candidates),
        debug=dict(rules.debug),
    )
    if mode == "rules" or not (text or "").strip():
        if mode == "hybrid":
            base.method = "hybrid:rules"
        return base

    weak = needs_llm(rules, settings.hybrid_confidence_threshold) if mode == "hybrid" else list(FIELDS)
    if mode == "hybrid" and not weak:
        base.method = "hybrid:rules"
        return base

    llm = llm or get_llm(settings)
    if not llm.available:
        base.method = "hybrid:rules" if mode == "hybrid" else "rules"
        if mode == "llm" or settings.llm_provider != "none":
            warnings.append(f"LLM unavailable ({llm.unavailable_reason}), used rules")
        return base
    hint = {k: rules.fields.get(k) for k in FIELDS}
    try:
        res = llm.extract(text, now, hint)
    except (LLMError, LLMUnavailable) as exc:
        warnings.append(f"LLM failed ({exc}), used rules")
        base.method = "hybrid:rules" if mode == "hybrid" else "rules"
        return base
    except Exception as exc:  # defensive: an unexpected bug in a provider must not crash the app
        warnings.append(f"LLM error ({type(exc).__name__}: {exc}), used rules")
        base.method = "hybrid:rules" if mode == "hybrid" else "rules"
        return base

    lf = _llm_fields(res.output, now)
    base.debug["llm_ms"] = round(res.ms, 1)
    base.debug["llm_cached"] = res.cached
    threshold = settings.review_confidence_threshold
    if mode == "llm":
        conf = {k: (0.8 if lf.get(k) is not None else 0.0) for k in FIELDS}
        if lf.get("merchant") and get_gazetteer().canonical(lf["merchant"]) is None:
            conf["merchant"] = 0.55
        base.fields = lf
        base.confidence = conf
        base.field_sources = {k: "llm" for k in FIELDS}
        base.method = "llm"
        base.needs_review = _review_list(lf, conf, threshold, set())
        return base

    fields, conf, sources, extra = merge(rules, lf, settings.hybrid_confidence_threshold)
    keep_rule_flags = {f for f in rules.needs_review if sources.get(f) == "rules" and f in ("date", "time", "amount")}
    base.fields = fields
    base.confidence = conf
    base.field_sources = sources
    base.method = "hybrid:llm_merged" if any(v == "llm" for v in sources.values()) else "hybrid:rules"
    base.needs_review = _review_list(fields, conf, threshold, extra | keep_rule_flags)
    if lf.get("category") and all(c["category"] != lf["category"] for c in base.category_candidates):
        base.category_candidates = (base.category_candidates + [{"category": lf["category"], "score": 0.3, "source": "llm"}])[:2]
    return base
