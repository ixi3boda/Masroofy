"""Optional LLM extraction with strict JSON output.

WHY an LLM at all, if the rules work offline?
    Rules cannot cover every way people talk ("حق الكهربائي اللي صلح النور").
    An LLM understands free speech much better, but it costs money, needs the
    internet (unless you run Ollama locally), can be slow, and can invent
    things. So we use it only as a helper:
      * it gets the transcript AND the rule-based draft as hints;
      * it must answer with JSON only, which we validate with pydantic;
      * invalid answers get ONE retry with the validation error, then we give up;
      * any failure (no key, no package, timeout, bad JSON) is reported as a
        warning and the rule result is kept. Nothing here ever crashes the app.

Providers (env LLM_PROVIDER):
    none              - default, LLM disabled
    anthropic         - Claude via the `anthropic` package and ANTHROPIC_API_KEY
    openai_compatible - any OpenAI-compatible server via the `openai` package:
                        api.openai.com, or local Ollama at http://localhost:11434/v1
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from concurrent.futures import ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass
from datetime import date as date_type
from datetime import datetime
from pathlib import Path
from typing import Any, Literal, Optional, Protocol

from pydantic import BaseModel, ValidationError, field_validator

from .categories import category_ids, load_categories
from .config import Settings

logger = logging.getLogger("voice_expense.llm")

PROMPT_VERSION = "v1"
# A small shared pool so a hanging provider can never block the pipeline beyond LLM_TIMEOUT_S.
_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="llm")


class LLMUnavailable(Exception):
    """The provider cannot be used (not configured, package or key missing)."""


class LLMError(Exception):
    """The provider was called but the answer could not be used."""


class LLMClient(Protocol):
    name: str
    model: str

    def complete(self, system: str, user: str) -> str:
        """Send the system + user prompt and return the model's raw text answer."""


# ---------------------------------------------------------------------------
# Providers (SDKs are imported lazily so they stay optional)
# ---------------------------------------------------------------------------
class AnthropicClient:
    name = "anthropic"

    def __init__(self, api_key: str, model: str, timeout_s: float) -> None:
        if not api_key:
            raise LLMUnavailable("ANTHROPIC_API_KEY is not set")
        try:
            import anthropic  # type: ignore
        except Exception as exc:  # pragma: no cover - depends on installed packages
            raise LLMUnavailable(f"package 'anthropic' not installed ({exc}); pip install -r requirements-llm.txt")
        self.model = model
        self._client = anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=1)

    def complete(self, system: str, user: str) -> str:
        # No `temperature`: claude-haiku-5-5 (the default) rejects non-default sampling values with a 400.
        # max_tokens has room for the model's built-in thinking before the short JSON answer.
        resp = self._client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        parts = [getattr(block, "text", "") for block in resp.content if getattr(block, "type", "") == "text"]
        return "".join(parts)


class OpenAICompatibleClient:
    name = "openai_compatible"

    def __init__(self, api_key: str, base_url: str, model: str, timeout_s: float) -> None:
        if not api_key and not base_url:
            raise LLMUnavailable("OPENAI_API_KEY is not set (for local Ollama set OPENAI_BASE_URL and any key)")
        try:
            import openai  # type: ignore
        except Exception as exc:  # pragma: no cover
            raise LLMUnavailable(f"package 'openai' not installed ({exc}); pip install -r requirements-llm.txt")
        self.model = model
        kwargs: dict[str, Any] = {"api_key": api_key or "ollama", "timeout": timeout_s, "max_retries": 1}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = openai.OpenAI(**kwargs)

    def complete(self, system: str, user: str) -> str:
        resp = self._client.chat.completions.create(
            model=self.model,
            temperature=0,
            messages=[{"role": "system", "content": system}, {"role": "user", "content": user}],
        )
        return resp.choices[0].message.content or ""


def make_client(settings: Settings) -> tuple[Optional[LLMClient], Optional[str]]:
    """Create the configured client. Returns (client, None) or (None, reason it is unavailable)."""
    provider = settings.llm_provider
    if provider == "none":
        return None, "LLM_PROVIDER=none"
    try:
        if provider == "anthropic":
            return AnthropicClient(settings.anthropic_api_key, settings.effective_llm_model, settings.llm_timeout_s), None
        if provider == "openai_compatible":
            return (
                OpenAICompatibleClient(settings.openai_api_key, settings.openai_base_url,
                                       settings.effective_llm_model, settings.llm_timeout_s),
                None,
            )
    except LLMUnavailable as exc:
        return None, str(exc)
    except Exception as exc:  # pragma: no cover - unexpected SDK init errors
        return None, f"could not create {provider} client: {exc}"
    return None, f"unknown LLM_PROVIDER={provider}"


# ---------------------------------------------------------------------------
# Output schema
# ---------------------------------------------------------------------------
class LLMOutput(BaseModel):
    """What the LLM must return. Unknown keys are ignored."""

    transaction_type: Literal["expense", "income"] = "expense"
    amount: Optional[float] = None
    currency: str = "EGP"
    merchant: Optional[str] = None
    category: str = "other"
    date: Optional[str] = None
    time: Optional[str] = None
    payment_method: Literal["cash", "card", "wallet", "unknown"] = "unknown"
    note: Optional[str] = None

    @field_validator("amount")
    @classmethod
    def _amount(cls, v: Optional[float]) -> Optional[float]:
        if v is None:
            return None
        if v <= 0:
            raise ValueError("amount must be a positive number or null")
        return v

    @field_validator("currency")
    @classmethod
    def _currency(cls, v: str) -> str:
        v = (v or "EGP").strip().upper()
        if not re.fullmatch(r"[A-Z]{3}", v):
            raise ValueError("currency must be a 3-letter ISO code")
        return v

    @field_validator("category")
    @classmethod
    def _category(cls, v: str) -> str:
        if v not in category_ids():
            raise ValueError(f"category must be one of {category_ids()}")
        return v

    @field_validator("date")
    @classmethod
    def _date(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        date_type.fromisoformat(v)  # raises ValueError if not YYYY-MM-DD
        return v

    @field_validator("time")
    @classmethod
    def _time(cls, v: Optional[str]) -> Optional[str]:
        if v in (None, ""):
            return None
        if not re.fullmatch(r"([01]?\d|2[0-3]):[0-5]\d", v):
            raise ValueError("time must be HH:MM (24h) or null")
        h, m = v.split(":")
        return f"{int(h):02d}:{m}"

    @field_validator("merchant", "note")
    @classmethod
    def _empty_to_none(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return None
        v = v.strip()
        return v or None


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------
FEW_SHOTS: list[tuple[str, dict[str, Any]]] = [
    ("دفعت 150 جنيه في Uber امبارح",
     {"transaction_type": "expense", "amount": 150, "currency": "EGP", "merchant": "Uber", "category": "transport",
      "date": "2026-11-19", "time": None, "payment_method": "unknown", "note": None}),
    ("صرفت 250 على groceries",
     {"transaction_type": "expense", "amount": 250, "currency": "EGP", "merchant": None, "category": "groceries",
      "date": "2026-11-20", "time": None, "payment_method": "unknown", "note": "groceries"}),
    ("I paid 80 pounds for coffee at Cilantro this morning",
     {"transaction_type": "expense", "amount": 80, "currency": "EGP", "merchant": "Cilantro", "category": "food_dining",
      "date": "2026-11-20", "time": "09:00", "payment_method": "unknown", "note": "coffee"}),
    ("اشتريت شاحن من B.Tech بألف وخمسمية جنيه فيزا",
     {"transaction_type": "expense", "amount": 1500, "currency": "EGP", "merchant": "B.Tech", "category": "electronics",
      "date": "2026-11-20", "time": None, "payment_method": "card", "note": "شاحن"}),
    ("dafa3t 300 cash lel doktor yom el khamis",
     {"transaction_type": "expense", "amount": 300, "currency": "EGP", "merchant": None, "category": "health",
      "date": "2026-11-19", "time": None, "payment_method": "cash", "note": "doktor"}),
    ("قبضت المرتب 15 ألف اتحولي انستاباي",
     {"transaction_type": "income", "amount": 15000, "currency": "EGP", "merchant": None, "category": "income",
      "date": "2026-11-20", "time": None, "payment_method": "wallet", "note": "المرتب"}),
    ("حق الكهربائي اللي صلح النور ميتين وخمسين الساعة 7 بالليل",
     {"transaction_type": "expense", "amount": 250, "currency": "EGP", "merchant": None, "category": "housing",
      "date": "2026-11-20", "time": "19:00", "payment_method": "unknown", "note": "الكهربائي صلح النور"}),
    ("spent 20 dollars on Netflix last Friday",
     {"transaction_type": "expense", "amount": 20, "currency": "USD", "merchant": "Netflix", "category": "subscriptions",
      "date": "2026-11-13", "time": None, "payment_method": "unknown", "note": None}),
]
FEW_SHOT_REFERENCE = "2026-11-20 (Friday) 14:00, Africa/Cairo"


def build_system_prompt(now: datetime) -> str:
    cats = "\n".join(f"- {c.id}: {c.en} / {c.ar}" for c in load_categories())
    shots = "\n\n".join(
        f"Input: {text}\nOutput: {json.dumps(out, ensure_ascii=False)}" for text, out in FEW_SHOTS
    )
    return f"""You extract ONE financial transaction from a short spoken sentence.
The sentence may be Egyptian Arabic, English, a mix of both, or Franco-Arabic (Arabic written with Latin letters and digits like 3=ع, 7=ح, 2=ء).

Return JSON ONLY (no prose, no code fences) with exactly these keys:
{{"transaction_type": "expense"|"income", "amount": number|null, "currency": ISO code, "merchant": string|null,
 "category": one id from the list, "date": "YYYY-MM-DD", "time": "HH:MM"|null,
 "payment_method": "cash"|"card"|"wallet"|"unknown", "note": string|null}}

Rules:
- amount is the money paid or received, always positive. null if no amount is said. Ignore quantities (2 كيلو), times (الساعة 3) and dates.
- Egyptian number words: مية=100, ميتين=200, خمسمية=500, ألف=1000, ألف ونص=1500, مية ونص=150, ربع=0.25.
- Default currency is EGP when none is said. جنيه/pounds/LE = EGP. استرليني/£ = GBP.
- merchant: the shop/brand/app name in its usual Latin spelling (أوبر -> Uber, كارفور -> Carrefour); null if none.
- category must be one of these ids:
{cats}
- An explicit category word beats the merchant's usual category (clothes at Carrefour = shopping).
- payment_method: كاش/cash=cash; فيزا/visa/card/كارت=card; instapay/vodafone cash/محفظة=wallet; otherwise unknown.
- Today is {now.strftime('%Y-%m-%d (%A) %H:%M')} in Africa/Cairo. Resolve امبارح/yesterday, weekdays (most recent past one), "من يومين" relative to today. Default date is today.
- Time-of-day words: الصبح/morning=09:00, الضهر/noon=13:00, العصر=16:00, بالليل/night=21:00.
- note: short leftover description words (item bought), or null.

Examples (reference date for the examples: {FEW_SHOT_REFERENCE}):

{shots}"""


def build_user_prompt(transcript: str, rule_hint: dict[str, Any]) -> str:
    hint = {k: (str(v) if v is not None else None) for k, v in rule_hint.items()}
    return (
        f"Transcript: {transcript}\n"
        f"Rule-based draft (may be wrong or incomplete, use it only as a hint): {json.dumps(hint, ensure_ascii=False)}\n"
        "Return the JSON object now."
    )


def parse_llm_json(text: str) -> dict[str, Any]:
    """Strip code fences and return the first JSON object in `text`."""
    if not text:
        raise LLMError("empty response")
    t = text.strip()
    t = re.sub(r"^```(?:json)?\s*", "", t)
    t = re.sub(r"\s*```$", "", t)
    start = t.find("{")
    if start < 0:
        raise LLMError("no JSON object in response")
    depth = 0
    in_str = False
    esc = False
    for k in range(start, len(t)):
        ch = t[k]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    obj = json.loads(t[start : k + 1])
                except json.JSONDecodeError as exc:
                    raise LLMError(f"invalid JSON: {exc}")
                if not isinstance(obj, dict):
                    raise LLMError("JSON is not an object")
                return obj
    raise LLMError("unterminated JSON object")


@dataclass
class LLMResult:
    output: LLMOutput
    raw: str
    cached: bool
    ms: float
    attempts: int


class LLMExtractor:
    """Calls the configured LLM, validates, retries once, caches answers on disk."""

    def __init__(self, settings: Settings, client: Optional[LLMClient] = None) -> None:
        self.settings = settings
        if client is not None:
            self.client: Optional[LLMClient] = client
            self.unavailable_reason: Optional[str] = None
        else:
            self.client, self.unavailable_reason = make_client(settings)

    @property
    def available(self) -> bool:
        return self.client is not None

    def _cache_path(self, transcript: str, now: datetime) -> Path:
        model = getattr(self.client, "model", "")
        key = f"{PROMPT_VERSION}|{getattr(self.client, 'name', '')}|{model}|{now.date().isoformat()}|{transcript}"
        h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:32]
        return Path(self.settings.llm_cache_dir) / f"{h}.json"

    def extract(self, transcript: str, now: datetime, rule_hint: dict[str, Any]) -> LLMResult:
        if self.client is None:
            raise LLMUnavailable(self.unavailable_reason or "LLM not configured")
        t0 = time.perf_counter()
        cache_file = self._cache_path(transcript, now)
        if self.settings.llm_cache and cache_file.is_file():
            try:
                raw = json.loads(cache_file.read_text(encoding="utf-8"))["raw"]
                out = LLMOutput.model_validate(parse_llm_json(raw))
                return LLMResult(out, raw, True, (time.perf_counter() - t0) * 1000, 0)
            except Exception:
                logger.warning("Ignoring unreadable LLM cache file %s", cache_file)
        system = build_system_prompt(now)
        user = build_user_prompt(transcript, rule_hint)
        last_error = ""
        raw = ""
        for attempt in (1, 2):
            prompt = user if attempt == 1 else (
                f"{user}\n\nYour previous answer was invalid: {last_error}\n"
                f"Previous answer: {raw[:500]}\nReturn ONLY a corrected JSON object."
            )
            future = _EXECUTOR.submit(self.client.complete, system, prompt)
            try:
                raw = future.result(timeout=self.settings.llm_timeout_s + 1.0)
            except FutureTimeout:
                future.cancel()
                raise LLMError(f"timeout after {self.settings.llm_timeout_s:.0f}s")
            except Exception as exc:
                raise LLMError(f"{type(exc).__name__}: {exc}")
            try:
                out = LLMOutput.model_validate(parse_llm_json(raw))
            except (LLMError, ValidationError) as exc:
                last_error = str(exc).splitlines()[0] if str(exc) else type(exc).__name__
                continue
            if self.settings.llm_cache:
                try:
                    cache_file.parent.mkdir(parents=True, exist_ok=True)
                    cache_file.write_text(json.dumps({"raw": raw}, ensure_ascii=False), encoding="utf-8")
                except OSError as exc:
                    logger.warning("Could not write LLM cache: %s", exc)
            return LLMResult(out, raw, False, (time.perf_counter() - t0) * 1000, attempt)
        raise LLMError(f"invalid LLM output after retry: {last_error}")
