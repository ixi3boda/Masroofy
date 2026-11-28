"""Speech-to-text (ASR) behind one small interface, with pluggable backends.

WHY several backends:
    * faster_whisper  - best default: runs Whisper on CPU (int8) or GPU (float16)
                        without torch, and decodes audio files itself.
    * openai_api      - cloud transcription; only used if OPENAI_API_KEY is set.
    * mock            - reads a text file next to the audio ("clip.wav" ->
                        "clip.txt" or "clip.wav.txt"). It needs nothing, so the
                        WHOLE pipeline, the tests and the smoke test run offline.

`ASR_BACKEND=auto` tries them in that order and says which one it picked and
why. If a backend fails at runtime (e.g. the model cannot be downloaded
because there is no internet) auto mode falls back to the next one with a
warning instead of crashing.

Why force Arabic by default (ASR_LANGUAGE=ar)? Whisper's language detection
often picks English for code-switched Egyptian speech and then translates or
garbles the Arabic part. Forcing "ar" keeps Arabic words in Arabic script and
the initial prompt (see config) nudges it to keep brand names in Latin and
numbers as digits. The evaluation script can compare ar vs auto.
"""
from __future__ import annotations

import logging
import os
import sys
import time
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .config import Settings, get_settings

logger = logging.getLogger("voice_expense.asr")

SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac", ".mp4", ".aac", ".opus", ".oga"}

# Phrases Whisper is known to invent on silence or music (from subtitle training data).
HALLUCINATIONS = [
    "ترجمة نانسي قنقر", "نانسي قنقر", "اشتركوا في القناة", "اشترك في القناة", "شكرا للمشاهدة",
    "شكراً للمشاهدة", "thanks for watching", "thank you for watching", "subscribe to",
    "please subscribe", "subtitles by", "amara.org", "[music]", "(music)", "♪",
]


class AudioValidationError(ValueError):
    """Bad input file. `error_code` is returned by the API."""

    def __init__(self, error_code: str, message: str) -> None:
        super().__init__(message)
        self.error_code = error_code
        self.message = message


class ASRBackendError(RuntimeError):
    """A backend could not run (missing package, model download failed...)."""


@dataclass
class ASRResult:
    text: str
    language: Optional[str]
    duration_s: Optional[float]
    asr_ms: float
    backend: str
    segments: list[dict[str, Any]] = field(default_factory=list)
    model_load_ms: float = 0.0
    warnings: list[str] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------
def audio_duration(path: Path) -> Optional[float]:
    """Duration in seconds, or None if we cannot tell without heavy libraries."""
    if path.suffix.lower() == ".wav":
        try:
            with wave.open(str(path), "rb") as w:
                frames = w.getnframes()
                rate = w.getframerate() or 1
                return frames / float(rate)
        except (wave.Error, EOFError, OSError):
            pass
    try:
        import soundfile as sf  # type: ignore

        return float(sf.info(str(path)).duration)
    except Exception:
        return None


def validate_audio(audio_path: str | os.PathLike[str], max_duration_s: float = 60.0) -> tuple[Path, Optional[float]]:
    """Check the file exists, has a supported extension, is not empty and not too long."""
    path = Path(audio_path)
    if not path.is_file():
        raise AudioValidationError("audio_not_found", f"Audio file not found: {path}")
    if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise AudioValidationError(
            "unsupported_audio_format",
            f"Unsupported audio format '{path.suffix}'. Use one of: {', '.join(sorted(SUPPORTED_EXTENSIONS))}",
        )
    if path.stat().st_size == 0:
        raise AudioValidationError("empty_audio", "The audio file is empty (0 bytes).")
    duration = audio_duration(path)
    if duration is not None:
        if duration <= 0.05:
            raise AudioValidationError("empty_audio", "The recording has no audio (duration is 0 s).")
        if duration > max_duration_s:
            raise AudioValidationError(
                "audio_too_long", f"Recording is {duration:.1f} s; the limit is {max_duration_s:.0f} s."
            )
    return path, duration


def _clean_hallucinations(text: str) -> tuple[str, list[str]]:
    warnings: list[str] = []
    cleaned = text
    low = cleaned.lower()
    for phrase in HALLUCINATIONS:
        if phrase.lower() in low:
            idx = low.find(phrase.lower())
            cleaned = cleaned[:idx] + cleaned[idx + len(phrase):]
            low = cleaned.lower()
            warnings.append(f"Removed a typical Whisper hallucination: '{phrase}'")
    return " ".join(cleaned.split()).strip(" .،,"), warnings


# ---------------------------------------------------------------------------
# Backends
# ---------------------------------------------------------------------------
class MockBackend:
    """Reads the transcript from a sidecar .txt file. Always available."""

    name = "mock"

    def transcribe(self, path: Path, language: Optional[str], settings: Settings) -> ASRResult:
        t0 = time.perf_counter()
        candidates = [path.with_suffix(".txt"), Path(str(path) + ".txt")]
        for c in candidates:
            if c.is_file():
                text = c.read_text(encoding="utf-8").strip()
                return ASRResult(text, language, None, (time.perf_counter() - t0) * 1000, self.name)
        return ASRResult(
            "", language, None, (time.perf_counter() - t0) * 1000, self.name,
            warnings=[f"Mock ASR: no transcript file found next to the audio (expected {candidates[0].name})."],
        )


_FW_MODELS: dict[tuple[str, str, str], Any] = {}
_GPU_BROKEN = False  # set once a GPU run failed because CUDA libraries are missing
_GPU_LIB_HINTS = ("cublas", "cudnn", "cuda", "libcu", "cufft", "nvrtc", ".dll")


def _looks_like_missing_gpu_libs(message: str) -> bool:
    low = message.lower()
    return any(h in low for h in _GPU_LIB_HINTS)


def _cuda_available() -> bool:
    try:
        import ctranslate2  # type: ignore  # installed with faster-whisper

        return ctranslate2.get_cuda_device_count() > 0
    except Exception:
        return False


def decode_audio_16k(path: Path) -> Any:
    """Decode any audio file to a 16 kHz mono float32 numpy array using PyAV.

    WHY we do this ourselves: faster-whisper 1.2.x calls `av.open(..., metadata_errors=...)`,
    an argument that newer PyAV versions (15+) removed, so it crashes on every file.
    Decoding here with plain `av.open(path)` works with old and new PyAV, and faster-whisper
    accepts the decoded array directly.
    """
    import av  # type: ignore  # installed with faster-whisper
    import numpy as np  # type: ignore

    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    chunks: list[Any] = []
    container = av.open(str(path), mode="r")
    try:
        for frame in container.decode(audio=0):
            frame.pts = None
            for out in resampler.resample(frame):
                chunks.append(out.to_ndarray())
        for out in resampler.resample(None):  # flush what is left in the resampler
            chunks.append(out.to_ndarray())
    finally:
        container.close()
    if not chunks:
        return np.zeros(0, dtype=np.float32)
    pcm = np.concatenate([c.reshape(-1) for c in chunks])
    return pcm.astype(np.float32) / 32768.0


class FasterWhisperBackend:
    name = "faster_whisper"

    def __init__(self) -> None:
        try:
            import faster_whisper  # type: ignore  # noqa: F401
        except Exception as exc:
            raise ASRBackendError(f"faster-whisper not installed ({exc}); pip install -r requirements-asr.txt")

    def _load(self, settings: Settings, force_device: Optional[str] = None) -> tuple[Any, float, str]:
        from faster_whisper import WhisperModel  # type: ignore

        device = force_device or settings.whisper_device
        if device == "auto":
            device = "cpu" if _GPU_BROKEN else ("cuda" if _cuda_available() else "cpu")
        compute_type = "float16" if device == "cuda" else "int8"
        key = (settings.whisper_model, device, compute_type)
        if key in _FW_MODELS:
            return _FW_MODELS[key], 0.0, device
        t0 = time.perf_counter()
        try:
            model = WhisperModel(settings.whisper_model, device=device, compute_type=compute_type)
        except Exception as exc:
            if device == "cuda" and _looks_like_missing_gpu_libs(str(exc)):
                raise ASRBackendError(f"CUDA libraries missing: {exc}")
            raise ASRBackendError(
                f"could not load Whisper model '{settings.whisper_model}' on {device} "
                f"(first use downloads it from the internet): {exc}"
            )
        _FW_MODELS[key] = model
        return model, (time.perf_counter() - t0) * 1000, device

    def transcribe(self, path: Path, language: Optional[str], settings: Settings) -> ASRResult:
        try:
            return self._transcribe(path, language, settings, None)
        except ASRBackendError as exc:
            if not _looks_like_missing_gpu_libs(str(exc)):
                raise
            # A GPU is visible but CUDA/cuBLAS/cuDNN are not installed (very common on Windows laptops).
            # Remember that, and run the same model on the CPU instead.
            global _GPU_BROKEN
            _GPU_BROKEN = True
            logger.warning("GPU libraries missing (%s); retrying faster-whisper on CPU.", exc)
            res = self._transcribe(path, language, settings, "cpu")
            res.warnings.append(
                "GPU found but its CUDA 12 libraries (cuBLAS/cuDNN) are not installed, so Whisper ran on the CPU. "
                "Set WHISPER_DEVICE=cpu in .env to skip the GPU attempt."
            )
            return res

    def _transcribe(self, path: Path, language: Optional[str], settings: Settings,
                    force_device: Optional[str]) -> ASRResult:
        model, load_ms, device = self._load(settings, force_device)
        t0 = time.perf_counter()
        lang = None if language in (None, "auto") else language
        audio_input: Any = str(path)
        decoded_duration: Optional[float] = None
        try:
            audio_input = decode_audio_16k(path)
            decoded_duration = len(audio_input) / 16000.0
        except Exception as exc:  # fall back to letting faster-whisper open the file itself
            logger.info("Own audio decoding failed (%s); passing the file path to faster-whisper.", exc)
        if decoded_duration is not None:
            if decoded_duration < 0.05:
                return ASRResult("", lang, decoded_duration, (time.perf_counter() - t0) * 1000,
                                 f"{self.name}:{settings.whisper_model}:{device}", model_load_ms=load_ms,
                                 warnings=["The recording contains no audio samples."])
            if decoded_duration > settings.asr_max_duration_s:
                raise AudioValidationError(
                    "audio_too_long",
                    f"Recording is {decoded_duration:.1f} s; the limit is {settings.asr_max_duration_s:.0f} s.")
        try:
            segments_iter, info = model.transcribe(
                audio_input,
                language=lang,
                beam_size=5,
                vad_filter=True,
                initial_prompt=settings.asr_initial_prompt or None,
            )
            segments = [{"start": round(s.start, 2), "end": round(s.end, 2), "text": s.text.strip()} for s in segments_iter]
        except Exception as exc:
            raise ASRBackendError(f"faster-whisper failed to transcribe {path.name}: {exc}")
        text = " ".join(s["text"] for s in segments).strip()
        return ASRResult(
            text=text,
            language=getattr(info, "language", lang),
            duration_s=decoded_duration if decoded_duration is not None else getattr(info, "duration", None),
            asr_ms=(time.perf_counter() - t0) * 1000,
            backend=f"{self.name}:{settings.whisper_model}:{device}",
            segments=segments,
            model_load_ms=load_ms,
        )


class OpenAIAPIBackend:
    name = "openai_api"

    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise ASRBackendError("OPENAI_API_KEY is not set")
        try:
            import openai  # type: ignore  # noqa: F401
        except Exception as exc:
            raise ASRBackendError(f"package 'openai' not installed ({exc}); pip install -r requirements-llm.txt")

    def transcribe(self, path: Path, language: Optional[str], settings: Settings) -> ASRResult:
        import openai  # type: ignore

        kwargs: dict[str, Any] = {"api_key": settings.openai_api_key, "timeout": 60.0}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        client = openai.OpenAI(**kwargs)
        t0 = time.perf_counter()
        try:
            with open(path, "rb") as fh:
                params: dict[str, Any] = {"model": settings.openai_asr_model, "file": fh}
                if language not in (None, "auto"):
                    params["language"] = language
                if settings.asr_initial_prompt:
                    params["prompt"] = settings.asr_initial_prompt
                resp = client.audio.transcriptions.create(**params)
        except Exception as exc:
            raise ASRBackendError(f"OpenAI transcription failed: {exc}")
        return ASRResult(
            text=str(getattr(resp, "text", "")).strip(),
            language=language,
            duration_s=None,
            asr_ms=(time.perf_counter() - t0) * 1000,
            backend=f"{self.name}:{settings.openai_asr_model}",
        )


def _make(name: str, settings: Settings) -> Any:
    if name == "mock":
        return MockBackend()
    if name == "faster_whisper":
        return FasterWhisperBackend()
    if name == "openai_api":
        return OpenAIAPIBackend(settings)
    raise ASRBackendError(f"unknown ASR backend '{name}'")


def backend_chain(settings: Settings, requested: Optional[str] = None) -> tuple[list[Any], list[str]]:
    """Backends to try, in order, plus messages explaining the choice."""
    name = (requested or settings.asr_backend or "auto").lower()
    messages: list[str] = []
    if name != "auto":
        try:
            return [_make(name, settings)], [f"ASR backend '{name}' selected by setting."]
        except ASRBackendError as exc:
            messages.append(f"ASR backend '{name}' unavailable: {exc}. Falling back to mock.")
            return [MockBackend()], messages
    chain: list[Any] = []
    for candidate in ("faster_whisper", "openai_api"):
        try:
            chain.append(_make(candidate, settings))
        except ASRBackendError as exc:
            messages.append(f"auto: skipped {candidate} ({exc})")
    chain.append(MockBackend())
    messages.append(f"auto: using {chain[0].name}" + (" (no real ASR available)" if chain[0].name == "mock" else ""))
    return chain, messages


def describe_backend(settings: Optional[Settings] = None) -> str:
    """Name of the backend that `transcribe` would try first (for /health)."""
    settings = settings or get_settings()
    chain, _ = backend_chain(settings)
    return chain[0].name


def transcribe(audio_path: str | os.PathLike[str], language: Optional[str] = None,
               settings: Optional[Settings] = None, backend: Optional[str] = None) -> ASRResult:
    """Validate the file and transcribe it. Raises AudioValidationError for bad input only."""
    settings = settings or get_settings()
    path, duration = validate_audio(audio_path, settings.asr_max_duration_s)
    lang = (language or settings.asr_language or "ar").lower()
    chain, messages = backend_chain(settings, backend)
    for m in messages:
        logger.info(m)
    warnings: list[str] = [m for m in messages if "unavailable" in m]
    if chain[0].name == "mock" and (backend or settings.asr_backend or "auto").lower() == "auto":
        # Say clearly WHY no real speech-to-text ran (the usual cause: requirements-asr.txt
        # was installed into a different Python environment than the one running the app).
        warnings.append(
            "No real speech-to-text is installed in THIS Python environment, so the mock backend was used. "
            f"Fix: run '{sys.executable} -m pip install -r requirements-asr.txt' and restart. Details: "
            + "; ".join(m for m in messages if m.startswith("auto: skipped"))
        )
    for b in chain:
        try:
            res = b.transcribe(path, lang, settings)
        except ASRBackendError as exc:
            warnings.append(f"{b.name} failed: {exc}. Trying next backend.")
            logger.warning("ASR backend %s failed: %s", b.name, exc)
            continue
        if res.duration_s is None:
            res.duration_s = duration
        if res.duration_s is not None and res.duration_s > settings.asr_max_duration_s:
            raise AudioValidationError("audio_too_long",
                                       f"Recording is {res.duration_s:.1f} s; the limit is {settings.asr_max_duration_s:.0f} s.")
        cleaned, hw = _clean_hallucinations(res.text)
        res.text = cleaned
        res.warnings = warnings + res.warnings + hw
        if not res.text:
            res.warnings.append("ASR returned no speech (silence, noise or a very short clip).")
        return res
    # Unreachable in practice because MockBackend never raises, kept for safety.
    return ASRResult("", lang, duration, 0.0, "none", warnings=warnings + ["No ASR backend could run."])
