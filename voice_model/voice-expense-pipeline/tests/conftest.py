"""Shared test fixtures.

Every test runs offline with a clean environment: rules-only extraction, mock
ASR, no LLM, a temporary SQLite file, and a fixed reference time
(Friday 2026-11-20 14:00 Africa/Cairo).
"""
from __future__ import annotations

import math
import struct
import sys
import wave
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice_expense.config import resolve_now  # noqa: E402

REF = "2026-11-20T14:00:00+02:00"
FIXTURES = Path(__file__).resolve().parent / "fixtures"


@pytest.fixture(autouse=True)
def clean_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setenv("ASR_BACKEND", "mock")
    monkeypatch.setenv("EXTRACTOR_MODE", "rules")
    monkeypatch.setenv("LLM_PROVIDER", "none")
    monkeypatch.setenv("LLM_CACHE", "0")
    monkeypatch.setenv("LLM_CACHE_DIR", str(tmp_path / "llm_cache"))
    monkeypatch.setenv("DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("ANTHROPIC_API_KEY", "")
    monkeypatch.setenv("OPENAI_API_KEY", "")
    monkeypatch.setenv("ASR_MAX_DURATION_S", "60")


@pytest.fixture
def now():
    return resolve_now(REF)


def write_wav(path: Path, seconds: float = 1.0, freq: float = 440.0, silent: bool = False, rate: int = 16000) -> Path:
    """Write a tiny mono 16-bit WAV with Python's built-in `wave` module (no binary files in git)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    n = int(seconds * rate)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        frames = bytearray()
        for i in range(n):
            v = 0 if silent else int(8000 * math.sin(2 * math.pi * freq * i / rate))
            frames += struct.pack("<h", v)
        w.writeframes(bytes(frames))
    return path


@pytest.fixture(scope="session")
def audio_fixtures() -> dict[str, Path]:
    """tests/fixtures/: tone_ar.wav (+.txt), tone_mixed.wav (+.wav.txt), silence.wav (no transcript)."""
    FIXTURES.mkdir(parents=True, exist_ok=True)
    ar = write_wav(FIXTURES / "tone_ar.wav", 0.5)
    (FIXTURES / "tone_ar.txt").write_text("دفعت ٣٠٠ كاش للدكتور يوم الخميس اللي فات", encoding="utf-8")
    mixed = write_wav(FIXTURES / "tone_mixed.wav", 0.5, freq=660)
    (FIXTURES / "tone_mixed.wav.txt").write_text("دفعت 150 جنيه في Uber امبارح", encoding="utf-8")
    silence = write_wav(FIXTURES / "silence.wav", 0.5, silent=True)
    return {"ar": ar, "mixed": mixed, "silence": silence}
