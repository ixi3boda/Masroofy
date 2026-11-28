"""10-second offline smoke test. Run this FIRST after installing requirements.txt.

    python scripts/smoke_test.py

Checks: 6 text examples (2 Arabic, 2 English, 2 mixed), 1 mock-audio example
(it writes its own tiny WAV + transcript in a temp folder) and 1 REST API call
through FastAPI's TestClient. Prints PASS/FAIL with expected vs got and exits
with code 0 only if everything passed. No internet, no models, no API keys.
"""
from __future__ import annotations

import math
import os
import struct
import sys
import tempfile
import time
import wave
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

# Force a fully offline, deterministic configuration for this run.
_TMP = tempfile.mkdtemp(prefix="voice_expense_smoke_")
os.environ.update({
    "ASR_BACKEND": "mock",
    "EXTRACTOR_MODE": "rules",
    "LLM_PROVIDER": "none",
    "LLM_CACHE": "0",
    "DB_PATH": str(Path(_TMP) / "smoke.db"),
})

REF = "2026-11-20T14:00:00+02:00"

TEXT_CASES: list[tuple[str, str, dict[str, Any]]] = [
    ("ar", "دفعت ٣٠٠ كاش للدكتور يوم الخميس اللي فات",
     {"amount": 300.0, "currency": "EGP", "category": "health", "date": "2026-11-19", "payment_method": "cash"}),
    ("ar", "اشتريت شاحن من بي تك بألف وخمسمية جنيه",
     {"amount": 1500.0, "merchant": "B.Tech", "category": "electronics"}),
    ("en", "I paid 80 pounds for coffee at Cilantro this morning",
     {"amount": 80.0, "merchant": "Cilantro", "category": "food_dining", "time": "09:00"}),
    ("en", "Spent 250 EGP on groceries yesterday",
     {"amount": 250.0, "category": "groceries", "date": "2026-11-19", "merchant": None}),
    ("mixed", "دفعت 150 جنيه في Uber",
     {"amount": 150.0, "merchant": "Uber", "category": "transport", "date": "2026-11-20"}),
    ("mixed", "صرفت 250 على groceries امبارح",
     {"amount": 250.0, "currency": "EGP", "category": "groceries", "date": "2026-11-19", "merchant": None}),
]


def _setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def _write_wav(path: Path, seconds: float = 0.5) -> None:
    rate = 16000
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"".join(struct.pack("<h", int(6000 * math.sin(2 * math.pi * 440 * i / rate)))
                               for i in range(int(seconds * rate))))


def _compare(draft_json: dict[str, Any], expected: dict[str, Any]) -> list[str]:
    problems = []
    for k, v in expected.items():
        got = draft_json.get(k)
        if isinstance(v, float):
            ok = got is not None and abs(float(got) - v) < 0.01
        else:
            ok = got == v
        if not ok:
            problems.append(f"{k}: expected {v!r}, got {got!r}")
    return problems


def main() -> int:
    _setup_console()
    t0 = time.perf_counter()
    results: list[tuple[str, bool, str]] = []

    def check(name: str, fn: Callable[[], list[str]]) -> None:
        try:
            problems = fn()
        except Exception as exc:  # report, never crash
            problems = [f"{type(exc).__name__}: {exc}"]
        results.append((name, not problems, "; ".join(problems)))
        status = "PASS" if not problems else "FAIL"
        print(f"[{status}] {name}" + ("" if not problems else f"\n        {'; '.join(problems)}"))

    try:
        from voice_expense import process_audio, process_text
    except Exception as exc:
        print(f"[FAIL] import voice_expense: {exc}\n       Did you run: pip install -r requirements.txt ?")
        return 1

    for lang, text, expected in TEXT_CASES:
        check(f"text/{lang}: {text}",
              lambda text=text, expected=expected: _compare(
                  process_text(text, now=REF, extractor="rules").model_dump(mode="json"), expected))

    def audio_check() -> list[str]:
        wav = Path(_TMP) / "clip.wav"
        _write_wav(wav)
        wav.with_suffix(".txt").write_text("دفعت 150 جنيه في Uber امبارح", encoding="utf-8")
        d = process_audio(wav, now=REF, asr_backend="mock", extractor="rules").model_dump(mode="json")
        return _compare(d, {"amount": 150.0, "merchant": "Uber", "date": "2026-11-19", "language": "mixed"})

    check("audio/mock: clip.wav + clip.txt", audio_check)

    def api_check() -> list[str]:
        try:
            from fastapi.testclient import TestClient
        except Exception as exc:
            return [f"fastapi/httpx not installed ({exc}). Run: pip install -r requirements.txt"]
        from voice_expense.api import app

        client = TestClient(app)
        r = client.post("/v1/expenses/parse-text",
                        json={"text": "دفعت 150 جنيه في Uber", "reference_time": REF, "extractor": "rules"})
        if r.status_code != 200:
            return [f"HTTP {r.status_code}: {r.text[:200]}"]
        return _compare(r.json(), {"amount": 150.0, "merchant": "Uber", "category": "transport"})

    check("api: POST /v1/expenses/parse-text (TestClient)", api_check)

    passed = sum(ok for _, ok, _ in results)
    elapsed = time.perf_counter() - t0
    print(f"\n{passed}/{len(results)} checks passed in {elapsed:.1f} s")
    if passed == len(results):
        print("SMOKE TEST PASSED ✅")
        return 0
    print("SMOKE TEST FAILED ❌ — see the FAIL lines above (docs/TESTING_GUIDE.md has fixes).")
    return 1


if __name__ == "__main__":
    sys.exit(main())
