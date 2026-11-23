"""Hybrid/LLM modes with FAKE providers (no network): fallbacks, retries, merging, cache."""
from __future__ import annotations

import json
import time
from decimal import Decimal

import pytest

from voice_expense.config import get_settings
from voice_expense.extractor import extract
from voice_expense.llm_extractor import LLMExtractor, make_client, parse_llm_json, LLMError
from voice_expense.pipeline import process_text


class FakeClient:
    name = "fake"
    model = "fake-1"

    def __init__(self, responses: list[str] | None = None, exc: Exception | None = None, delay: float = 0.0):
        self.responses = list(responses or [])
        self.exc = exc
        self.delay = delay
        self.calls: list[str] = []

    def complete(self, system: str, user: str) -> str:
        self.calls.append(user)
        if self.delay:
            time.sleep(self.delay)
        if self.exc:
            raise self.exc
        return self.responses.pop(0) if self.responses else "{}"


def _good(**kw) -> str:
    base = {"transaction_type": "expense", "amount": 75, "currency": "EGP", "merchant": "Zooba",
            "category": "food_dining", "date": "2026-11-20", "time": None, "payment_method": "unknown", "note": None}
    base.update(kw)
    return json.dumps(base)


def _llm(client: FakeClient, **settings_kw) -> LLMExtractor:
    s = get_settings().with_overrides(**settings_kw)
    return LLMExtractor(s, client=client)


def test_rules_mode_never_calls_llm(now) -> None:
    client = FakeClient([_good()])
    out = extract("دفعت 150 جنيه في Uber", now, mode="rules", llm=_llm(client))
    assert out.method == "rules" and client.calls == []


def test_hybrid_skips_llm_when_rules_confident(now) -> None:
    client = FakeClient([_good()])
    out = extract("دفعت 150 جنيه في اوبر امبارح", now, mode="hybrid", llm=_llm(client))
    assert out.method == "hybrid:rules" and client.calls == []


def test_hybrid_fallback_when_llm_raises(now) -> None:
    client = FakeClient(exc=RuntimeError("network down"))
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=_llm(client))
    assert out.method == "hybrid:rules"
    assert out.fields["category"] == "fuel"
    assert any("LLM failed" in w for w in out.warnings)


def test_invalid_json_retried_once_then_succeeds(now) -> None:
    client = FakeClient(["sorry, I cannot do JSON", "```json\n" + _good(amount=120, merchant=None, category="fuel") + "\n```"])
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=_llm(client))
    assert len(client.calls) == 2
    assert "previous answer was invalid" in client.calls[1]
    assert out.fields["amount"] == Decimal("120")
    assert out.method == "hybrid:llm_merged"
    assert out.field_sources["amount"] == "llm"


def test_invalid_json_twice_falls_back(now) -> None:
    client = FakeClient(["not json", '{"amount": -5, "category": "fuel"}'])
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=_llm(client))
    assert out.method == "hybrid:rules"
    assert out.fields["amount"] is None
    assert any("LLM failed" in w for w in out.warnings)


def test_category_outside_list_is_rejected(now) -> None:
    client = FakeClient([_good(category="food"), _good(category="not_a_category")])
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=_llm(client))
    assert out.method == "hybrid:rules"


def test_merge_keeps_confident_rule_values(now) -> None:
    # Rules: 300 next to "جنيه" (confident). LLM disagrees on the amount -> rules win.
    client = FakeClient([_good(amount=999, merchant=None, category="gifts_donations")])
    out = extract("دفعت 300 جنيه", now, mode="hybrid", llm=_llm(client))
    assert out.fields["amount"] == Decimal("300")
    assert out.field_sources["amount"] == "rules"
    assert out.fields["category"] == "gifts_donations"  # rules said "other" -> LLM fills it
    assert out.field_sources["category"] == "llm"


def test_llm_mode_uses_llm_values(now) -> None:
    client = FakeClient([_good(amount=75, merchant="Zooba")])
    out = extract("اتعشيت في زووبا بخمسة وسبعين", now, mode="llm", llm=_llm(client))
    assert out.method == "llm" and out.fields["merchant"] == "Zooba"


def test_missing_api_key_is_a_warning_not_an_error(now, monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "anthropic")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    s = get_settings()
    client, reason = make_client(s)
    assert client is None and "ANTHROPIC_API_KEY" in (reason or "")
    d = process_text("دفعت تمن البنزين امبارح", now=now, extractor="hybrid", settings=s)
    assert d.extraction_method == "hybrid:rules"
    assert any("LLM unavailable" in w for w in d.warnings)


def test_openai_compatible_without_key_or_url(monkeypatch) -> None:
    monkeypatch.setenv("LLM_PROVIDER", "openai_compatible")
    client, reason = make_client(get_settings())
    assert client is None and reason


def test_llm_mode_without_provider_falls_back_to_rules(now) -> None:
    d = process_text("دفعت 150 جنيه في Uber", now=now, extractor="llm")
    assert d.extraction_method == "rules"
    assert any("LLM unavailable" in w for w in d.warnings)


def test_timeout(now) -> None:
    client = FakeClient([_good()], delay=3.0)
    llm = _llm(client, llm_timeout_s=0.2)
    t0 = time.perf_counter()
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=llm)
    assert time.perf_counter() - t0 < 2.5
    assert any("timeout" in w for w in out.warnings)


def test_cache_avoids_second_call(now, tmp_path) -> None:
    client = FakeClient([_good(amount=50, merchant=None, category="fuel")])
    llm = _llm(client, llm_cache=True, llm_cache_dir=str(tmp_path / "cache"))
    extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=llm)
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=llm)
    assert len(client.calls) == 1 and out.fields["amount"] == Decimal("50")


def test_parse_llm_json() -> None:
    assert parse_llm_json('Here you go: {"a": {"b": "}"}} trailing')["a"]["b"] == "}"
    with pytest.raises(LLMError):
        parse_llm_json("no braces at all")


# --- provider integrations, checked with fake SDK modules (no network) ----------------------
def test_anthropic_client_with_fake_sdk(monkeypatch, now) -> None:
    import sys
    import types

    from voice_expense.llm_extractor import AnthropicClient

    seen: dict = {}

    class _Block:
        type = "text"
        text = _good(amount=33, merchant=None, category="fuel")

    class _Messages:
        def create(self, **kw):  # type: ignore[no-untyped-def]
            seen.update(kw)
            return types.SimpleNamespace(content=[_Block()])

    class Anthropic:
        def __init__(self, api_key: str, timeout: float, max_retries: int) -> None:
            seen["init"] = (api_key, timeout, max_retries)
            self.messages = _Messages()

    mod = types.ModuleType("anthropic")
    mod.Anthropic = Anthropic  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "anthropic", mod)
    client = AnthropicClient("sk-test", "claude-haiku-5-5", 15.0)
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=_llm(client))  # type: ignore[arg-type]
    assert out.fields["amount"] == Decimal("33") and out.method == "hybrid:llm_merged"
    assert seen["model"] == "claude-haiku-5-5" and seen["init"][0] == "sk-test"
    assert "Africa/Cairo" in seen["system"]


def test_openai_compatible_client_with_fake_sdk(monkeypatch, now) -> None:
    import sys
    import types

    from voice_expense.llm_extractor import OpenAICompatibleClient

    seen: dict = {}

    class _Completions:
        def create(self, **kw):  # type: ignore[no-untyped-def]
            seen.update(kw)
            msg = types.SimpleNamespace(content=_good(amount=44, merchant=None, category="fuel"))
            return types.SimpleNamespace(choices=[types.SimpleNamespace(message=msg)])

    class OpenAI:
        def __init__(self, **kw) -> None:  # type: ignore[no-untyped-def]
            seen["init"] = kw
            self.chat = types.SimpleNamespace(completions=_Completions())

    mod = types.ModuleType("openai")
    mod.OpenAI = OpenAI  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "openai", mod)
    client = OpenAICompatibleClient("", "http://localhost:11434/v1", "qwen2.5:7b", 10.0)
    out = extract("دفعت تمن البنزين امبارح", now, mode="hybrid", llm=_llm(client))  # type: ignore[arg-type]
    assert out.fields["amount"] == Decimal("44")
    assert seen["init"]["base_url"] == "http://localhost:11434/v1" and seen["model"] == "qwen2.5:7b"
