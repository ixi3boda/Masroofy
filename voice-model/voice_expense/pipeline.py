"""The public entry points: `process_text` and `process_audio`.

WHY a thin pipeline module:
    The CLI, the REST API, the Gradio demo, the smoke test and the evaluation
    all call exactly these two functions, so they all behave the same way.
    Each stage is timed (asr, normalize, extract, total) because the project
    proposal asks us to report how long processing takes.

Nothing is saved here. The result is a *draft*; only `storage.save_confirmed`
(called after the user confirms) writes to the database.
"""
from __future__ import annotations

import os
import time
from datetime import datetime
from typing import Optional

from .asr import ASRResult, transcribe
from .config import Settings, get_settings, resolve_now
from .extractor import FIELDS, extract
from .llm_extractor import LLMExtractor
from .normalize import normalize_text
from .schemas import ExpenseDraft, Timings


def _build_draft(text: str, now: datetime, settings: Settings, mode: Optional[str],
                 llm: Optional[LLMExtractor], asr: Optional[ASRResult], t_start: float) -> ExpenseDraft:
    t0 = time.perf_counter()
    normalize_text(text)  # timed separately; extract() normalizes again internally (cheap)
    t_norm = (time.perf_counter() - t0) * 1000
    t1 = time.perf_counter()
    out = extract(text, now, settings=settings, mode=mode, llm=llm)
    t_extract = (time.perf_counter() - t1) * 1000
    warnings = list(asr.warnings if asr else []) + list(settings.warnings) + list(out.warnings)
    needs_review = list(out.needs_review)
    if not text.strip():
        needs_review = [f for f in FIELDS if f != "note"]
    total = (time.perf_counter() - t_start) * 1000
    timings = Timings(
        asr=round(asr.asr_ms, 1) if asr else 0.0,
        normalize=round(t_norm, 2),
        extract=round(t_extract, 2),
        total=round(total, 1),
        model_load=round(asr.model_load_ms, 1) if asr else 0.0,
    )
    f = out.fields
    return ExpenseDraft(
        transaction_type=f["transaction_type"],
        amount=f["amount"],
        currency=f["currency"],
        merchant=f["merchant"],
        category=f["category"],
        date=f["date"],
        time=f["time"],
        payment_method=f["payment_method"],
        note=f["note"],
        confidence={k: round(float(v), 2) for k, v in out.confidence.items()},
        needs_review=needs_review,
        language=out.language,  # type: ignore[arg-type]
        transcript=text,
        normalized_text=out.normalized_text,
        extraction_method=out.method,  # type: ignore[arg-type]
        warnings=warnings,
        timings_ms=timings,
        reference_time=now,
        category_candidates=out.category_candidates,
        field_sources=out.field_sources,
    )


def process_text(text: str, now: Optional[datetime | str] = None, extractor: Optional[str] = None,
                 settings: Optional[Settings] = None, llm: Optional[LLMExtractor] = None) -> ExpenseDraft:
    """Turn typed/transcribed text into an ExpenseDraft.

    now:       reference time for relative dates (default: current Cairo time)
    extractor: "rules" | "llm" | "hybrid" (default: EXTRACTOR_MODE setting)
    """
    t_start = time.perf_counter()
    settings = settings or get_settings()
    ref = resolve_now(now, settings.timezone_name)
    return _build_draft(text or "", ref, settings, extractor, llm, None, t_start)


def process_audio(path: str | os.PathLike[str], now: Optional[datetime | str] = None,
                  language: Optional[str] = None, extractor: Optional[str] = None,
                  asr_backend: Optional[str] = None, settings: Optional[Settings] = None,
                  llm: Optional[LLMExtractor] = None) -> ExpenseDraft:
    """Transcribe an audio file, then extract. Raises asr.AudioValidationError for bad files only."""
    t_start = time.perf_counter()
    settings = settings or get_settings()
    ref = resolve_now(now, settings.timezone_name)
    asr = transcribe(path, language=language, settings=settings, backend=asr_backend)
    draft = _build_draft(asr.text, ref, settings, extractor, llm, asr, t_start)
    draft.warnings = list(dict.fromkeys(draft.warnings + [f"ASR backend: {asr.backend}"]))
    return draft
