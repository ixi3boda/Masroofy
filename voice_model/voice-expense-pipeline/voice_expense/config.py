"""Settings for the whole pipeline.

WHY this module exists:
    Every tunable value (which ASR backend, which LLM, thresholds, file paths)
    lives in one place so teammates change behaviour through a `.env` file
    instead of editing code.

Design rules:
    * Loading settings must NEVER raise. A missing `.env`, a missing API key or
      a typo in a number falls back to a safe default and logs a warning.
    * `python-dotenv` is optional at import time: if it is not installed we just
      read real environment variables.
    * The timezone helper works on Windows too: Windows has no system timezone
      database, so `zoneinfo` needs the `tzdata` package. If neither is
      available we fall back to a fixed UTC+02:00 offset and warn.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field, replace
from datetime import datetime, timedelta, timezone, tzinfo
from pathlib import Path
from typing import Optional

logger = logging.getLogger("voice_expense")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_DIR = Path(__file__).resolve().parent
DATA_DIR = PACKAGE_DIR / "data"

DEFAULT_INITIAL_PROMPT = (
    "دفعت 150 جنيه في Uber امبارح. صرفت 250 على groceries. "
    "اشتريت من Carrefour بـ 320 جنيه."
)

_dotenv_loaded = False


def _load_dotenv_once() -> None:
    """Load `.env` from the current folder or the project root (only once)."""
    global _dotenv_loaded
    if _dotenv_loaded:
        return
    _dotenv_loaded = True
    try:
        from dotenv import load_dotenv  # type: ignore
    except Exception:  # pragma: no cover - only when python-dotenv is missing
        logger.warning("python-dotenv is not installed; reading settings from environment variables only.")
        return
    for candidate in (Path.cwd() / ".env", PROJECT_ROOT / ".env"):
        if candidate.is_file():
            # override=False: real environment variables win over the file.
            load_dotenv(candidate, override=False)
            break


def _get_str(name: str, default: str) -> str:
    value = os.environ.get(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _get_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    try:
        return float(raw)
    except ValueError:
        logger.warning("Setting %s=%r is not a number; using default %s", name, raw, default)
        return default


def _get_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


@dataclass
class Settings:
    """All runtime settings with safe defaults. Create with `get_settings()`."""

    asr_backend: str = "auto"
    whisper_model: str = "small"
    whisper_device: str = "cpu"
    asr_language: str = "ar"
    asr_initial_prompt: str = DEFAULT_INITIAL_PROMPT
    asr_max_duration_s: float = 60.0
    max_upload_mb: float = 10.0
    openai_asr_model: str = "whisper-1"

    extractor_mode: str = "hybrid"
    hybrid_confidence_threshold: float = 0.6
    review_confidence_threshold: float = 0.6

    llm_provider: str = "none"
    llm_model: str = ""
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    openai_base_url: str = ""
    llm_timeout_s: float = 15.0
    llm_cache: bool = True
    llm_cache_dir: str = ".cache/llm"

    db_path: str = "expenses.db"
    timezone_name: str = "Africa/Cairo"
    default_currency: str = "EGP"
    log_level: str = "WARNING"

    warnings: list[str] = field(default_factory=list)

    def with_overrides(self, **kwargs: object) -> "Settings":
        """Return a copy with some fields replaced (None values are ignored)."""
        clean = {k: v for k, v in kwargs.items() if v is not None}
        return replace(self, **clean)

    @property
    def effective_llm_model(self) -> str:
        if self.llm_model:
            return self.llm_model
        if self.llm_provider == "anthropic":
            return "claude-haiku-5-5"
        if self.llm_provider == "openai_compatible":
            return "gpt-4o-mini"
        return ""


def get_settings() -> Settings:
    """Read settings from the environment (and `.env`). Never raises."""
    _load_dotenv_once()
    s = Settings(
        asr_backend=_get_str("ASR_BACKEND", "auto").lower(),
        whisper_model=_get_str("WHISPER_MODEL", "small"),
        whisper_device=_get_str("WHISPER_DEVICE", "cpu").lower(),
        asr_language=_get_str("ASR_LANGUAGE", "ar").lower(),
        asr_initial_prompt=_get_str("ASR_INITIAL_PROMPT", DEFAULT_INITIAL_PROMPT),
        asr_max_duration_s=_get_float("ASR_MAX_DURATION_S", 60.0),
        max_upload_mb=_get_float("MAX_UPLOAD_MB", 10.0),
        openai_asr_model=_get_str("OPENAI_ASR_MODEL", "whisper-1"),
        extractor_mode=_get_str("EXTRACTOR_MODE", "hybrid").lower(),
        hybrid_confidence_threshold=_get_float("HYBRID_CONFIDENCE_THRESHOLD", 0.6),
        review_confidence_threshold=_get_float("REVIEW_CONFIDENCE_THRESHOLD", 0.6),
        llm_provider=_get_str("LLM_PROVIDER", "none").lower(),
        llm_model=_get_str("LLM_MODEL", ""),
        anthropic_api_key=_get_str("ANTHROPIC_API_KEY", ""),
        openai_api_key=_get_str("OPENAI_API_KEY", ""),
        openai_base_url=_get_str("OPENAI_BASE_URL", ""),
        llm_timeout_s=_get_float("LLM_TIMEOUT_S", 15.0),
        llm_cache=_get_bool("LLM_CACHE", True),
        llm_cache_dir=_get_str("LLM_CACHE_DIR", ".cache/llm"),
        db_path=_get_str("DB_PATH", "expenses.db"),
        timezone_name=_get_str("TIMEZONE", "Africa/Cairo"),
        default_currency=_get_str("DEFAULT_CURRENCY", "EGP").upper(),
        log_level=_get_str("LOG_LEVEL", "WARNING").upper(),
    )
    if s.extractor_mode not in {"rules", "llm", "hybrid"}:
        s.warnings.append(f"Unknown EXTRACTOR_MODE={s.extractor_mode!r}; using 'hybrid'.")
        s.extractor_mode = "hybrid"
    if s.llm_provider not in {"none", "anthropic", "openai_compatible"}:
        s.warnings.append(f"Unknown LLM_PROVIDER={s.llm_provider!r}; using 'none'.")
        s.llm_provider = "none"
    if s.asr_language not in {"auto", "ar", "en"}:
        s.warnings.append(f"Unknown ASR_LANGUAGE={s.asr_language!r}; using 'ar'.")
        s.asr_language = "ar"
    for w in s.warnings:
        logger.warning(w)
    try:
        logging.basicConfig(level=getattr(logging, s.log_level, logging.WARNING))
    except Exception:  # pragma: no cover
        pass
    return s


_tz_cache: dict[str, tzinfo] = {}
_tz_warned = False


def get_timezone(name: str = "Africa/Cairo") -> tzinfo:
    """Return the tzinfo for `name`, falling back to fixed UTC+2 if unavailable.

    WHY: all relative dates ("امبارح", "last Friday") must be resolved in Cairo
    time. On Windows without `tzdata`, ZoneInfo raises; we must not crash.
    """
    global _tz_warned
    if name in _tz_cache:
        return _tz_cache[name]
    tz: tzinfo
    try:
        from zoneinfo import ZoneInfo

        tz = ZoneInfo(name)
    except Exception:
        if not _tz_warned:
            logger.warning(
                "Timezone %s not found (install the 'tzdata' package). Using fixed UTC+02:00.", name
            )
            _tz_warned = True
        tz = timezone(timedelta(hours=2), "EET")
    _tz_cache[name] = tz
    return tz


def resolve_now(now: Optional[datetime | str] = None, tz_name: str = "Africa/Cairo") -> datetime:
    """Turn `now` (None, naive datetime, aware datetime or ISO string) into an aware Cairo datetime.

    WHY: every date computation takes an explicit reference time so tests and
    evaluation are deterministic. Naive values are interpreted as Cairo local time.
    """
    tz = get_timezone(tz_name)
    if now is None:
        return datetime.now(tz)
    if isinstance(now, str):
        text = now.strip()
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        try:
            parsed = datetime.fromisoformat(text)
        except ValueError:
            from dateutil import parser as du_parser

            parsed = du_parser.parse(text)
        now = parsed
    if now.tzinfo is None:
        return now.replace(tzinfo=tz)
    return now.astimezone(tz)
