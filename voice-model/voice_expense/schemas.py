"""Pydantic (v2) data models shared by the pipeline, the API and the app.

WHY pydantic:
    The mobile app talks to us through JSON. Pydantic checks every value
    (types, ranges, allowed words) and generates the OpenAPI schema that
    Swagger (/docs) shows, so the API contract is documented automatically.

Money is stored as `Decimal` (no floating point rounding surprises) with two
decimal places. In JSON it is sent as a number, for example 150.0, because
mobile developers find that easier than a string. See docs/DECISIONS.md.
"""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Any, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field, field_serializer, field_validator

TransactionType = Literal["expense", "income"]
PaymentMethod = Literal["cash", "card", "wallet", "unknown"]
Language = Literal["ar", "en", "mixed"]
ExtractionMethod = Literal["rules", "llm", "hybrid:rules", "hybrid:llm_merged"]

# Fields that the user can see and edit in the review screen.
EDITABLE_FIELDS: tuple[str, ...] = (
    "transaction_type",
    "amount",
    "currency",
    "merchant",
    "category",
    "date",
    "time",
    "payment_method",
    "note",
)


def to_money(value: Any) -> Optional[Decimal]:
    """Convert any number-like value to a positive Decimal with 2 decimals (or None)."""
    if value is None or value == "":
        return None
    try:
        d = Decimal(str(value).replace(",", ""))
    except (InvalidOperation, ValueError):
        raise ValueError(f"amount {value!r} is not a number")
    if d.is_nan() or d.is_infinite():
        raise ValueError("amount must be a finite number")
    d = abs(d)
    return d.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Timings(BaseModel):
    """Milliseconds spent in each stage. `asr` is 0 for text input."""

    asr: float = 0.0
    normalize: float = 0.0
    extract: float = 0.0
    total: float = 0.0
    model_load: float = 0.0


class ExpenseDraft(BaseModel):
    """What the pipeline proposes. Nothing is saved until the user confirms it."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "transaction_type": "expense",
                    "amount": 150.0,
                    "currency": "EGP",
                    "merchant": "Uber",
                    "category": "transport",
                    "date": "2026-11-19",
                    "time": None,
                    "payment_method": "unknown",
                    "note": None,
                    "confidence": {"amount": 0.95, "merchant": 0.95, "category": 0.75, "date": 0.9},
                    "needs_review": [],
                    "language": "mixed",
                    "transcript": "دفعت 150 جنيه في Uber امبارح",
                    "normalized_text": "دفعت 150 جنيه في uber امبارح",
                    "extraction_method": "hybrid:rules",
                    "warnings": [],
                    "timings_ms": {"asr": 0, "normalize": 0.2, "extract": 1.5, "total": 1.9},
                    "reference_time": "2026-11-20T14:00:00+02:00",
                }
            ]
        }
    )

    transaction_type: TransactionType = "expense"
    amount: Optional[Decimal] = None
    currency: str = "EGP"
    merchant: Optional[str] = None
    category: str = "other"
    date: date_type
    time: Optional[str] = None
    payment_method: PaymentMethod = "unknown"
    note: Optional[str] = None
    confidence: dict[str, float] = Field(default_factory=dict)
    needs_review: list[str] = Field(default_factory=list)
    language: Language = "ar"
    transcript: str = ""
    normalized_text: str = ""
    extraction_method: ExtractionMethod = "rules"
    warnings: list[str] = Field(default_factory=list)
    timings_ms: Timings = Field(default_factory=Timings)
    reference_time: datetime
    # Debug helpers (safe for the app to ignore).
    category_candidates: list[dict[str, Any]] = Field(default_factory=list)
    field_sources: dict[str, str] = Field(default_factory=dict)

    @field_validator("amount", mode="before")
    @classmethod
    def _amount(cls, v: Any) -> Optional[Decimal]:
        return to_money(v)

    @field_validator("currency")
    @classmethod
    def _currency(cls, v: str) -> str:
        v = (v or "EGP").strip().upper()
        if len(v) != 3 or not v.isalpha():
            raise ValueError("currency must be a 3-letter ISO code such as EGP or USD")
        return v

    @field_validator("time")
    @classmethod
    def _time(cls, v: Optional[str]) -> Optional[str]:
        if v is None or v == "":
            return None
        parts = v.split(":")
        if len(parts) < 2 or not parts[0].isdigit() or not parts[1].isdigit():
            raise ValueError("time must look like HH:MM")
        hh, mm = int(parts[0]), int(parts[1])
        if not (0 <= hh <= 23 and 0 <= mm <= 59):
            raise ValueError("time must be between 00:00 and 23:59")
        return f"{hh:02d}:{mm:02d}"

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        # Imported lazily to avoid a circular import at module load.
        from .categories import category_ids

        return v if v in category_ids() else "other"

    @field_serializer("amount", when_used="json")
    def _ser_amount(self, v: Optional[Decimal]) -> Optional[float]:
        return None if v is None else float(v)


class ConfirmRequest(BaseModel):
    """Sent by the app when the user taps Confirm.

    `draft` is the draft exactly as the pipeline returned it. `corrections`
    holds only the fields the user changed, e.g. {"amount": 200}. Keeping them
    separate lets us measure how often users correct each field.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "draft": ExpenseDraft.model_config["json_schema_extra"]["examples"][0],  # type: ignore[index]
                    "corrections": {"amount": 160, "payment_method": "card"},
                }
            ]
        }
    )

    draft: ExpenseDraft
    corrections: dict[str, Any] = Field(default_factory=dict)

    @field_validator("corrections")
    @classmethod
    def _only_editable(cls, v: dict[str, Any]) -> dict[str, Any]:
        unknown = [k for k in v if k not in EDITABLE_FIELDS]
        if unknown:
            raise ValueError(f"cannot correct unknown fields: {unknown}; allowed: {list(EDITABLE_FIELDS)}")
        return v


class ConfirmedTransaction(ExpenseDraft):
    """A saved transaction: the final (possibly corrected) draft plus storage info."""

    id: int
    created_at: datetime
    user_edited_fields: list[str] = Field(default_factory=list)


class ParseTextRequest(BaseModel):
    """Body of POST /v1/expenses/parse-text."""

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "text": "صرفت 250 على groceries امبارح",
                    "reference_time": "2026-11-20T14:00:00+02:00",
                    "extractor": "rules",
                }
            ]
        }
    )

    text: str = Field(..., min_length=1, max_length=1000)
    reference_time: Optional[datetime] = None
    extractor: Optional[Literal["rules", "llm", "hybrid"]] = None


class ErrorResponse(BaseModel):
    """Every API error has this shape."""

    error_code: str
    message: str
