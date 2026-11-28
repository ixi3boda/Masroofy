"""Generate synthetic speech for every dataset phrase (for ASR + end-to-end evaluation).

Usage:
    pip install -r requirements-audio-gen.txt
    python eval/generate_audio.py --limit 20
    python eval/generate_audio.py --engine gtts

Engines, tried in this order (or forced with --engine):
    edge    edge-tts, Microsoft neural voices (internet). Egyptian voices
            ar-EG-SalmaNeural / ar-EG-ShakirNeural for Arabic and mixed,
            en-US voices for English. Voices alternate between examples.
    gtts    Google Translate TTS (internet), lang "ar" or "en".
    espeak  espeak-ng command (offline, robotic quality).

Output: eval/audio/synthetic/<id>.mp3 (or .wav for espeak) and manifest.csv.
Existing files are skipped, so you can stop and resume.

IMPORTANT: TTS audio is far cleaner than a real person talking in a café, so
results on it are optimistic. Use eval/record_audio.py for honest numbers.
"""
from __future__ import annotations

import argparse
import asyncio
import csv
import json
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "eval" / "dataset" / "phrases.jsonl"
DEFAULT_OUT = ROOT / "eval" / "audio" / "synthetic"

EDGE_VOICES = {
    "ar": ["ar-EG-SalmaNeural", "ar-EG-ShakirNeural"],
    "mixed": ["ar-EG-SalmaNeural", "ar-EG-ShakirNeural"],
    "en": ["en-US-JennyNeural", "en-US-GuyNeural"],
    "franco": ["en-US-JennyNeural", "en-US-GuyNeural"],
}
INSTALL_HELP = """No text-to-speech engine is available.
Install one of these and run the script again:
  pip install edge-tts        (best quality, needs internet; Egyptian Arabic voices)
  pip install gTTS            (needs internet)
  espeak-ng                   (offline): Ubuntu/Colab: apt-get install -y espeak-ng ; macOS: brew install espeak-ng
Or simply: pip install -r requirements-audio-gen.txt
"""


def _setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def available_engines() -> list[str]:
    engines = []
    try:
        import edge_tts  # type: ignore  # noqa: F401

        engines.append("edge")
    except Exception:
        pass
    try:
        import gtts  # type: ignore  # noqa: F401

        engines.append("gtts")
    except Exception:
        pass
    if shutil.which("espeak-ng") or shutil.which("espeak"):
        engines.append("espeak")
    return engines


async def _edge(text: str, voice: str, path: Path) -> None:
    import edge_tts  # type: ignore

    communicate = edge_tts.Communicate(text, voice)
    await communicate.save(str(path))


def _gtts(text: str, lang_group: str, path: Path) -> None:
    from gtts import gTTS  # type: ignore

    gTTS(text=text, lang="en" if lang_group in ("en", "franco") else "ar").save(str(path))


def _espeak(text: str, lang_group: str, path: Path) -> None:
    exe = shutil.which("espeak-ng") or shutil.which("espeak")
    if exe is None:
        raise RuntimeError("espeak-ng not found")
    voice = "en" if lang_group in ("en", "franco") else "ar"
    subprocess.run([exe, "-v", voice, "-w", str(path), text], check=True, capture_output=True, timeout=60)


def _read_manifest(path: Path) -> dict[str, dict[str, str]]:
    if not path.is_file():
        return {}
    with open(path, encoding="utf-8-sig", newline="") as fh:
        return {row["id"]: row for row in csv.DictReader(fh)}


def _write_manifest(path: Path, rows: dict[str, dict[str, str]]) -> None:
    fields = ["id", "path", "text", "lang_group", "tts_engine", "voice"]
    with open(path, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for row in rows.values():
            w.writerow({k: row.get(k, "") for k in fields})


async def generate(examples: list[dict[str, Any]], out_dir: Path, engines: list[str]) -> tuple[int, int, int]:
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / "manifest.csv"
    rows = _read_manifest(manifest_path)
    made = skipped = failed = 0
    for i, ex in enumerate(examples, 1):
        group = ex["lang_group"]
        existing = [p for p in (out_dir / f"{ex['id']}.mp3", out_dir / f"{ex['id']}.wav") if p.is_file() and p.stat().st_size > 0]
        if existing:
            skipped += 1
            if ex["id"] not in rows:
                rows[ex["id"]] = {"id": ex["id"], "path": existing[0].relative_to(ROOT).as_posix(), "text": ex["text"],
                                  "lang_group": group, "tts_engine": "existing", "voice": ""}
            continue
        done = False
        errors = []
        for engine in engines:
            voice = ""
            try:
                if engine == "edge":
                    voices = EDGE_VOICES.get(group, EDGE_VOICES["ar"])
                    voice = voices[i % len(voices)]
                    path = out_dir / f"{ex['id']}.mp3"
                    await _edge(ex["text"], voice, path)
                elif engine == "gtts":
                    voice = "gtts-" + ("en" if group in ("en", "franco") else "ar")
                    path = out_dir / f"{ex['id']}.mp3"
                    _gtts(ex["text"], group, path)
                else:
                    voice = "espeak-" + ("en" if group in ("en", "franco") else "ar")
                    path = out_dir / f"{ex['id']}.wav"
                    _espeak(ex["text"], group, path)
                if not path.is_file() or path.stat().st_size == 0:
                    raise RuntimeError("empty output file")
                rows[ex["id"]] = {"id": ex["id"], "path": path.relative_to(ROOT).as_posix(), "text": ex["text"],
                                  "lang_group": group, "tts_engine": engine, "voice": voice}
                made += 1
                done = True
                break
            except Exception as exc:  # network errors, missing voices...
                errors.append(f"{engine}: {type(exc).__name__}: {exc}")
        if not done:
            failed += 1
            print(f"  [{i}/{len(examples)}] {ex['id']} FAILED -> " + " | ".join(errors)[:300])
        else:
            print(f"  [{i}/{len(examples)}] {ex['id']} ok ({rows[ex['id']]['tts_engine']} {rows[ex['id']]['voice']})")
        _write_manifest(manifest_path, rows)
    _write_manifest(manifest_path, rows)
    return made, skipped, failed


def main(argv: Optional[list[str]] = None) -> int:
    _setup_console()
    ap = argparse.ArgumentParser(description="Generate synthetic audio for the dataset")
    ap.add_argument("--limit", type=int, default=None, help="only the first N examples")
    ap.add_argument("--engine", choices=["auto", "edge", "gtts", "espeak"], default="auto")
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET))
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args(argv)

    engines = available_engines()
    if args.engine != "auto":
        if args.engine not in engines:
            print(f"Engine '{args.engine}' is not available.\n{INSTALL_HELP}")
            return 0
        engines = [args.engine]
    if not engines:
        print(INSTALL_HELP)
        return 0
    examples = [json.loads(line) for line in open(args.dataset, encoding="utf-8") if line.strip()]
    if args.limit:
        # Take examples from every language group so a small run is still balanced.
        groups: dict[str, list[dict[str, Any]]] = {}
        for ex in examples:
            groups.setdefault(ex["lang_group"], []).append(ex)
        picked: list[dict[str, Any]] = []
        k = 0
        while len(picked) < min(args.limit, len(examples)):
            for g in groups.values():
                if k < len(g) and len(picked) < args.limit:
                    picked.append(g[k])
            k += 1
        examples = picked
    print(f"Engines available: {engines}. Generating {len(examples)} files into {args.out}")
    made, skipped, failed = asyncio.run(generate(examples, Path(args.out), engines))
    print(f"\nDone: {made} created, {skipped} already existed, {failed} failed.")
    print(f"Manifest: {Path(args.out) / 'manifest.csv'}")
    if failed and made == 0:
        print("All generations failed. Check your internet connection, or install espeak-ng for offline TTS.")
    print("Next: python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
