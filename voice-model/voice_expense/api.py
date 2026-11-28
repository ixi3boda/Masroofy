"""REST API used by the mobile app (FastAPI).

Run:  uvicorn voice_expense.api:app --reload      then open http://127.0.0.1:8000/docs

WHY these endpoints:
    parse-text / parse-audio return a DRAFT (nothing saved). The app shows it,
    highlights `needs_review` fields, lets the user edit, then calls confirm.
    Only confirm writes to the database and it stores which fields were
    edited, which gives us the real-world correction rate.

Every error has the same JSON shape: {"error_code": "...", "message": "..."}.
See docs/API.md for examples.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from . import __version__
from .asr import SUPPORTED_EXTENSIONS, AudioValidationError, describe_backend
from .config import get_settings, resolve_now
from .extractor import get_llm
from .pipeline import process_audio, process_text
from .schemas import ConfirmedTransaction, ConfirmRequest, ErrorResponse, ExpenseDraft, ParseTextRequest
from .storage import correction_stats, list_transactions, save_confirmed


class APIError(Exception):
    def __init__(self, status_code: int, error_code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.error_code = error_code
        self.message = message


_ERRORS: dict[int | str, dict[str, Any]] = {
    400: {"model": ErrorResponse, "description": "Bad input"},
    413: {"model": ErrorResponse, "description": "File or recording too large/long"},
    415: {"model": ErrorResponse, "description": "Unsupported audio format"},
    422: {"model": ErrorResponse, "description": "Validation error"},
}

app = FastAPI(
    title="Voice Expense Pipeline API",
    version=__version__,
    description=(
        "Turns a spoken or typed expense (Egyptian Arabic, English or mixed) into a draft transaction. "
        "The user reviews the draft and confirms it; only confirmed transactions are saved."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # development only; restrict to the app's origin in production
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def _api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error_code": exc.error_code, "message": exc.message})


@app.exception_handler(RequestValidationError)
async def _validation_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    parts = []
    for err in exc.errors():
        loc = ".".join(str(x) for x in err.get("loc", []) if x != "body")
        parts.append(f"{loc}: {err.get('msg', 'invalid')}" if loc else str(err.get("msg", "invalid")))
    return JSONResponse(status_code=422, content={"error_code": "validation_error", "message": "; ".join(parts)})


@app.exception_handler(StarletteHTTPException)
async def _http_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    code = {404: "not_found", 405: "method_not_allowed"}.get(exc.status_code, "http_error")
    return JSONResponse(status_code=exc.status_code, content={"error_code": code, "message": str(exc.detail)})


@app.exception_handler(Exception)
async def _unexpected_handler(request: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=500, content={"error_code": "internal_error", "message": f"{type(exc).__name__}: {exc}"})


def _parse_reference(value: Optional[str | datetime]) -> datetime:
    settings = get_settings()
    try:
        return resolve_now(value, settings.timezone_name)
    except (ValueError, OverflowError) as exc:
        raise APIError(422, "invalid_reference_time", f"reference_time is not a valid ISO datetime: {exc}")


@app.get("/", include_in_schema=False)
def root() -> RedirectResponse:
    """Opening the service in a browser shows the API docs instead of a 404."""
    return RedirectResponse(url="/docs")


@app.get("/health", summary="Service status")
def health() -> dict[str, Any]:
    settings = get_settings()
    llm = get_llm(settings)
    return {
        "status": "ok",
        "version": __version__,
        "asr_backend": describe_backend(settings),
        "asr_backend_setting": settings.asr_backend,
        "asr_language": settings.asr_language,
        "extractor_mode": settings.extractor_mode,
        "llm_provider": settings.llm_provider,
        "llm_available": llm.available,
        "llm_unavailable_reason": llm.unavailable_reason,
        "timezone": settings.timezone_name,
    }


@app.post("/v1/expenses/parse-text", response_model=ExpenseDraft, responses=_ERRORS, summary="Parse typed text")
def parse_text(req: ParseTextRequest) -> ExpenseDraft:
    if not req.text.strip():
        raise APIError(400, "empty_text", "text is empty")
    ref = _parse_reference(req.reference_time)
    return process_text(req.text, now=ref, extractor=req.extractor)


@app.post("/v1/expenses/parse-audio", response_model=ExpenseDraft, responses=_ERRORS, summary="Parse a voice recording")
async def parse_audio(
    file: UploadFile = File(..., description="wav / mp3 / m4a / ogg / webm recording, max 60 s"),
    reference_time: Optional[str] = Form(None, description="ISO datetime, e.g. 2026-11-20T14:00:00+02:00"),
    language: Optional[str] = Form(None, description="ar | en | auto (default from settings)"),
    extractor: Optional[str] = Form(None, description="rules | llm | hybrid"),
) -> ExpenseDraft:
    settings = get_settings()
    ref = _parse_reference(reference_time)
    if language is not None and language not in ("ar", "en", "auto"):
        raise APIError(422, "invalid_language", "language must be ar, en or auto")
    if extractor is not None and extractor not in ("rules", "llm", "hybrid"):
        raise APIError(422, "invalid_extractor", "extractor must be rules, llm or hybrid")
    suffix = Path(file.filename or "audio.wav").suffix.lower() or ".wav"
    if suffix not in SUPPORTED_EXTENSIONS:
        raise APIError(415, "unsupported_audio_format",
                       f"Unsupported audio format '{suffix}'. Use one of: {', '.join(sorted(SUPPORTED_EXTENSIONS))}")
    max_bytes = int(settings.max_upload_mb * 1024 * 1024)
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise APIError(413, "file_too_large", f"Upload is larger than {settings.max_upload_mb:.0f} MB")
    if not data:
        raise APIError(400, "empty_audio", "The uploaded file is empty")
    fd, tmp_path = tempfile.mkstemp(suffix=suffix, prefix="voice_expense_")
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
        try:
            return await run_in_threadpool(process_audio, tmp_path, ref, language, extractor)
        except AudioValidationError as exc:
            status = {"audio_too_long": 413, "unsupported_audio_format": 415}.get(exc.error_code, 400)
            raise APIError(status, exc.error_code, exc.message)
    finally:
        try:
            os.remove(tmp_path)
        except OSError:
            pass


@app.post("/v1/expenses/confirm", response_model=ConfirmedTransaction, status_code=201, responses=_ERRORS,
          summary="Confirm (and optionally correct) a draft; saves it")
def confirm(req: ConfirmRequest) -> ConfirmedTransaction:
    try:
        return save_confirmed(req)
    except ValidationError as exc:
        msg = "; ".join(f"{'.'.join(str(x) for x in e.get('loc', []))}: {e.get('msg')}" for e in exc.errors())
        raise APIError(422, "invalid_correction", msg)
    except ValueError as exc:
        if str(exc) == "amount_required":
            raise APIError(422, "amount_required", "An amount is required before saving. Please enter the amount.")
        raise APIError(422, "invalid_correction", str(exc))


@app.get("/v1/expenses", response_model=list[ConfirmedTransaction], summary="List saved transactions (newest first)")
def list_expenses(limit: int = 50) -> list[ConfirmedTransaction]:
    if limit < 1 or limit > 1000:
        raise APIError(422, "invalid_limit", "limit must be between 1 and 1000")
    return list_transactions(limit=limit)


@app.get("/v1/expenses/stats", summary="Real-usage correction statistics")
def stats() -> dict[str, Any]:
    return correction_stats()
