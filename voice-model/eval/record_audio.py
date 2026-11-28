"""Record real voices for the dataset phrases (the honest evaluation).

Usage:
    pip install sounddevice soundfile numpy
    python eval/record_audio.py --speaker ahmed
    python eval/record_audio.py --speaker ahmed --start-id mx_10      # resume
    python eval/record_audio.py --speaker ahmed --only-id ar_05       # re-record one phrase
    python eval/record_audio.py --speaker ahmed --scan                 # files recorded on a phone

Controls while recording: press Enter to START, Enter again to STOP.
Then: Enter = keep and go on, r = record again, s = skip, q = quit.

No microphone / no sounddevice? Record on your phone instead and copy the files
to eval/audio/real/<speaker>/<id>.wav (or .m4a/.mp3/.ogg), then run with
--scan to build the manifest. In Colab see docs/COLAB.md (upload the folder).

WHY: TTS voices are clean and always pronounce numbers the same way. Real
people mumble, code-switch differently and record in noisy rooms. The
proposal's numbers should come from these recordings.
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_DATASET = ROOT / "eval" / "dataset" / "phrases.jsonl"
REAL_DIR = ROOT / "eval" / "audio" / "real"
AUDIO_EXT = (".wav", ".m4a", ".mp3", ".ogg", ".webm", ".flac", ".aac", ".opus")

PHONE_HELP = """Microphone recording is not available here ({reason}).
Option A: pip install sounddevice soundfile numpy   (and make sure a microphone is connected)
Option B: record on your phone:
  1. Read each phrase from eval/dataset/phrases.jsonl naturally (as you would really say it).
  2. Name each file with the phrase id, e.g. ar_01.m4a, mx_12.m4a
  3. Copy them into eval/audio/real/{speaker}/
  4. Run: python eval/record_audio.py --speaker {speaker} --scan
"""


def _setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def load_examples(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in open(path, encoding="utf-8") if line.strip()]


def update_manifest(examples: list[dict[str, Any]]) -> Path:
    """(Re)build eval/audio/real/manifest.csv from every file found under eval/audio/real/<speaker>/."""
    by_id = {e["id"]: e for e in examples}
    rows = []
    REAL_DIR.mkdir(parents=True, exist_ok=True)
    for speaker_dir in sorted(p for p in REAL_DIR.iterdir() if p.is_dir()):
        for f in sorted(speaker_dir.iterdir()):
            if f.suffix.lower() in AUDIO_EXT and f.stem in by_id and f.stat().st_size > 0:
                ex = by_id[f.stem]
                rows.append({"id": f.stem, "path": f.relative_to(ROOT).as_posix(), "text": ex["text"],
                             "lang_group": ex["lang_group"], "speaker": speaker_dir.name})
    manifest = REAL_DIR / "manifest.csv"
    with open(manifest, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "path", "text", "lang_group", "speaker"])
        w.writeheader()
        w.writerows(rows)
    print(f"Manifest: {manifest} ({len(rows)} recordings)")
    return manifest


def _record_until_enter(sd: Any, np: Any, samplerate: int, max_seconds: float) -> Any:
    chunks: list[Any] = []

    def callback(indata: Any, frames: int, time_info: Any, status: Any) -> None:
        chunks.append(indata.copy())

    input("  Press Enter to START recording...")
    with sd.InputStream(samplerate=samplerate, channels=1, dtype="int16", callback=callback):
        input("  ...recording... press Enter to STOP.")
    if not chunks:
        return np.zeros((0, 1), dtype="int16")
    audio = np.concatenate(chunks, axis=0)
    return audio[: int(max_seconds * samplerate)]


def main(argv: Optional[list[str]] = None) -> int:
    _setup_console()
    ap = argparse.ArgumentParser(description="Record dataset phrases with your own voice")
    ap.add_argument("--speaker", default="speaker1", help="your name/id (folder name)")
    ap.add_argument("--start-id", help="start from this phrase id")
    ap.add_argument("--only-id", help="record only this phrase id (re-record)")
    ap.add_argument("--dataset", default=str(DEFAULT_DATASET))
    ap.add_argument("--samplerate", type=int, default=16000)
    ap.add_argument("--max-seconds", type=float, default=30.0)
    ap.add_argument("--scan", action="store_true", help="only rebuild the manifest from files already in the folder")
    args = ap.parse_args(argv)

    examples = load_examples(Path(args.dataset))
    speaker_dir = REAL_DIR / args.speaker
    speaker_dir.mkdir(parents=True, exist_ok=True)
    if args.scan:
        update_manifest(examples)
        return 0
    try:
        import numpy as np  # type: ignore
        import sounddevice as sd  # type: ignore
        import soundfile as sf  # type: ignore

        sd.query_devices(kind="input")
    except Exception as exc:
        print(PHONE_HELP.format(reason=f"{type(exc).__name__}: {exc}", speaker=args.speaker))
        update_manifest(examples)
        return 0

    todo = examples
    if args.only_id:
        todo = [e for e in examples if e["id"] == args.only_id]
        if not todo:
            print(f"No phrase with id {args.only_id}")
            return 1
    elif args.start_id:
        ids = [e["id"] for e in examples]
        if args.start_id not in ids:
            print(f"No phrase with id {args.start_id}")
            return 1
        todo = examples[ids.index(args.start_id):]

    print(f"Recording as '{args.speaker}' into {speaker_dir}. Say each phrase naturally, the way you really talk.")
    for n, ex in enumerate(todo, 1):
        out = speaker_dir / f"{ex['id']}.wav"
        if out.exists() and not args.only_id:
            print(f"[{n}/{len(todo)}] {ex['id']} already recorded (use --only-id {ex['id']} to redo)")
            continue
        while True:
            print(f"\n[{n}/{len(todo)}] {ex['id']} ({ex['lang_group']}):\n    {ex['text']}")
            audio = _record_until_enter(sd, np, args.samplerate, args.max_seconds)
            if len(audio) < args.samplerate * 0.3:
                print("  Too short / nothing recorded. Try again.")
                continue
            sf.write(str(out), audio, args.samplerate)
            choice = input(f"  Saved {len(audio) / args.samplerate:.1f}s. [Enter]=next  r=redo  s=skip  q=quit: ").strip().lower()
            if choice == "r":
                continue
            if choice == "s":
                out.unlink(missing_ok=True)
            if choice == "q":
                update_manifest(examples)
                return 0
            break
    update_manifest(examples)
    print("Next: python eval/evaluate.py --mode audio --manifest eval/audio/real/manifest.csv")
    return 0


if __name__ == "__main__":
    sys.exit(main())
