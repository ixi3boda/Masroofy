"""Audio path with the mock ASR backend (no model needed)."""
from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path

import pytest

from voice_expense.asr import AudioValidationError, backend_chain, transcribe, validate_audio
from voice_expense.config import get_settings
from voice_expense.pipeline import process_audio, process_text
from tests.conftest import write_wav


def test_mock_audio_end_to_end(audio_fixtures, now) -> None:
    d = process_audio(audio_fixtures["ar"], now=now)
    assert d.transcript.startswith("دفعت")
    assert d.amount == Decimal("300.00") and d.payment_method == "cash"
    assert d.date == date(2026, 11, 19)
    assert d.timings_ms.total >= d.timings_ms.asr >= 0
    assert any("mock" in w for w in d.warnings)


def test_sidecar_with_full_name(audio_fixtures, now) -> None:
    d = process_audio(audio_fixtures["mixed"], now=now)
    assert d.merchant == "Uber" and d.language == "mixed"


def test_missing_sidecar_gives_review_everything(audio_fixtures, now) -> None:
    d = process_audio(audio_fixtures["silence"], now=now)
    assert d.transcript == ""
    assert d.amount is None
    assert {"amount", "merchant", "category", "date"} <= set(d.needs_review)
    assert any("no transcript" in w.lower() for w in d.warnings)


def test_empty_text_does_not_crash(now) -> None:
    d = process_text("   ", now=now)
    assert d.amount is None and "amount" in d.needs_review


def test_file_not_found() -> None:
    with pytest.raises(AudioValidationError) as e:
        validate_audio("does/not/exist.wav")
    assert e.value.error_code == "audio_not_found"


def test_unsupported_extension(tmp_path: Path) -> None:
    p = tmp_path / "note.txt"
    p.write_text("hello")
    with pytest.raises(AudioValidationError) as e:
        validate_audio(p)
    assert e.value.error_code == "unsupported_audio_format"


def test_empty_file(tmp_path: Path) -> None:
    p = tmp_path / "empty.wav"
    p.write_bytes(b"")
    with pytest.raises(AudioValidationError) as e:
        transcribe(p)
    assert e.value.error_code == "empty_audio"


def test_too_long(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("ASR_MAX_DURATION_S", "1")
    p = write_wav(tmp_path / "long.wav", seconds=2.0, silent=True)
    with pytest.raises(AudioValidationError) as e:
        transcribe(p)
    assert e.value.error_code == "audio_too_long"


def test_auto_backend_always_ends_with_mock(monkeypatch) -> None:
    monkeypatch.setenv("ASR_BACKEND", "auto")
    chain, messages = backend_chain(get_settings())
    assert chain[-1].name == "mock"
    assert any("auto:" in m for m in messages)


def test_unavailable_explicit_backend_falls_back(monkeypatch, audio_fixtures, now) -> None:
    monkeypatch.setenv("ASR_BACKEND", "openai_api")  # no key set -> unavailable
    d = process_audio(audio_fixtures["ar"], now=now)
    assert d.amount == Decimal("300.00")
    assert any("unavailable" in w for w in d.warnings)


def test_hallucination_removed(tmp_path: Path, now) -> None:
    p = write_wav(tmp_path / "h.wav", 0.5, silent=True)
    (tmp_path / "h.txt").write_text("ترجمة نانسي قنقر", encoding="utf-8")
    d = process_audio(p, now=now)
    assert d.transcript == ""
    assert any("hallucination" in w for w in d.warnings)


# --- faster-whisper integration, checked with a fake module (no model download) -------------
class _Seg:
    def __init__(self, start: float, end: float, text: str) -> None:
        self.start, self.end, self.text = start, end, text


class _Info:
    language = "ar"
    duration = 0.5


def _fake_faster_whisper(fail_on_load: bool = False):  # type: ignore[no-untyped-def]
    import types

    mod = types.ModuleType("faster_whisper")
    calls: dict = {}

    class WhisperModel:
        def __init__(self, size: str, device: str = "cpu", compute_type: str = "int8") -> None:
            if fail_on_load:
                raise RuntimeError("cannot download model: no internet")
            calls["init"] = (size, device, compute_type)

        def transcribe(self, path: str, language=None, beam_size=5, vad_filter=False, initial_prompt=None):  # type: ignore[no-untyped-def]
            calls["transcribe"] = {"language": language, "beam_size": beam_size, "vad_filter": vad_filter,
                                   "initial_prompt": initial_prompt}
            return iter([_Seg(0.0, 0.5, " دفعت 150 جنيه في Uber امبارح")]), _Info()

    mod.WhisperModel = WhisperModel  # type: ignore[attr-defined]
    return mod, calls


def test_faster_whisper_backend(monkeypatch, audio_fixtures, now) -> None:
    import sys

    from voice_expense import asr

    mod, calls = _fake_faster_whisper()
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    monkeypatch.setattr(asr, "_FW_MODELS", {})
    monkeypatch.setenv("ASR_BACKEND", "faster_whisper")
    d = process_audio(audio_fixtures["silence"], now=now)
    assert d.merchant == "Uber" and d.amount == Decimal("150.00") and d.date == date(2026, 11, 19)
    assert calls["init"][2] in ("int8", "float16")
    assert calls["transcribe"]["language"] == "ar" and calls["transcribe"]["vad_filter"] is True
    assert calls["transcribe"]["beam_size"] == 5 and "Uber" in calls["transcribe"]["initial_prompt"]
    assert any("faster_whisper" in w for w in d.warnings)


def test_auto_falls_back_when_model_download_fails(monkeypatch, audio_fixtures, now) -> None:
    import sys

    from voice_expense import asr

    mod, _ = _fake_faster_whisper(fail_on_load=True)
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    monkeypatch.setattr(asr, "_FW_MODELS", {})
    monkeypatch.setenv("ASR_BACKEND", "auto")
    d = process_audio(audio_fixtures["ar"], now=now)
    assert d.amount == Decimal("300.00")  # mock backend read the sidecar
    assert any("faster_whisper failed" in w for w in d.warnings)


def test_auto_explains_why_mock_was_used(monkeypatch, audio_fixtures, now) -> None:
    import sys

    from voice_expense import asr

    monkeypatch.setenv("ASR_BACKEND", "auto")
    monkeypatch.setitem(sys.modules, "faster_whisper", None)  # simulate "not installed"
    monkeypatch.setitem(sys.modules, "whisper", None)
    monkeypatch.setattr(asr, "_FW_MODELS", {})
    d = process_audio(audio_fixtures["ar"], now=now)
    assert any("requirements-asr.txt" in w for w in d.warnings)


def test_faster_whisper_gets_decoded_array(monkeypatch, audio_fixtures, now) -> None:
    """Our own PyAV decoding (works with PyAV 15+), checked with a fake `av` module."""
    import sys
    import types

    np = pytest.importorskip("numpy")
    from voice_expense import asr

    class _Frame:
        pts = 0

        def __init__(self, n: int) -> None:
            self.n = n

        def to_ndarray(self):  # type: ignore[no-untyped-def]
            return np.full((1, self.n), 16384, dtype=np.int16)

    class _Resampler:
        def __init__(self, format: str, layout: str, rate: int) -> None:
            assert (format, layout, rate) == ("s16", "mono", 16000)

        def resample(self, frame):  # type: ignore[no-untyped-def]
            return [] if frame is None else [frame]

    class _Container:
        def decode(self, audio: int = 0):  # type: ignore[no-untyped-def]
            return iter([_Frame(8000), _Frame(8000)])

        def close(self) -> None:
            pass

    def _open(path: str, mode: str = "r"):  # no metadata_errors argument, like PyAV 15+
        return _Container()

    av = types.ModuleType("av")
    av.open = _open  # type: ignore[attr-defined]
    av.AudioResampler = _Resampler  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "av", av)
    fw, calls = _fake_faster_whisper()
    received: dict = {}
    original = fw.WhisperModel.transcribe

    def spy(self, audio, **kw):  # type: ignore[no-untyped-def]
        received["audio"] = audio
        return original(self, audio, **kw)

    fw.WhisperModel.transcribe = spy
    monkeypatch.setitem(sys.modules, "faster_whisper", fw)
    monkeypatch.setattr(asr, "_FW_MODELS", {})
    monkeypatch.setenv("ASR_BACKEND", "faster_whisper")
    d = process_audio(audio_fixtures["silence"], now=now)
    assert isinstance(received["audio"], np.ndarray) and received["audio"].dtype == np.float32
    assert len(received["audio"]) == 16000 and abs(float(received["audio"][0]) - 0.5) < 1e-6
    assert d.merchant == "Uber"


def test_gpu_without_cuda_libraries_falls_back_to_cpu(monkeypatch, audio_fixtures, now) -> None:
    import sys
    import types

    from voice_expense import asr

    devices: list = []

    class WhisperModel:
        def __init__(self, size: str, device: str = "cpu", compute_type: str = "int8") -> None:
            self.device = device
            devices.append((device, compute_type))

        def transcribe(self, audio, **kw):  # type: ignore[no-untyped-def]
            def gen():  # real faster-whisper fails lazily while iterating segments
                if self.device == "cuda":
                    raise RuntimeError("Library cublas64_12.dll is not found or cannot be loaded")
                yield _Seg(0.0, 0.5, "دفعت 150 جنيه في Uber امبارح")
            return gen(), _Info()

    mod = types.ModuleType("faster_whisper")
    mod.WhisperModel = WhisperModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "faster_whisper", mod)
    monkeypatch.setattr(asr, "_FW_MODELS", {})
    monkeypatch.setattr(asr, "_GPU_BROKEN", False)
    monkeypatch.setattr(asr, "_cuda_available", lambda: True)
    monkeypatch.setenv("WHISPER_DEVICE", "auto")
    monkeypatch.setenv("ASR_BACKEND", "faster_whisper")
    d = process_audio(audio_fixtures["silence"], now=now)
    assert devices == [("cuda", "float16"), ("cpu", "int8")]
    assert d.merchant == "Uber" and any("ran on the CPU" in w for w in d.warnings)
