"""Step 1 of the REAL dataset: create a spreadsheet to label real voice notes.

    python eval/make_label_sheet.py --audio-dir eval/audio/collected

It finds every audio file under --audio-dir (sub-folders = speakers) and writes
eval/dataset/real_labels.csv with one row per file and EMPTY label columns.
Open it in Excel, listen to each file and fill the row (rules in docs/REAL_DATASET.md),
then run eval/import_labels.py.

Running it again later only ADDS rows for new files; your labels are kept.

--prefill fills the transcript and fields with the app's own guesses so labelling is
faster. Be careful: people tend to accept wrong guesses, which makes the app look
better than it is. Without --prefill the labels are fully independent (recommended
for the numbers you put in the thesis).
"""
from __future__ import annotations

import argparse
import csv
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice_expense.asr import SUPPORTED_EXTENSIONS  # noqa: E402
from voice_expense.config import get_timezone  # noqa: E402

COLUMNS = [
    "file", "speaker", "lang_group", "reference_time", "transcript",
    "transaction_type", "amount", "currency", "merchant", "category", "date", "time", "time_word",
    "payment_method", "checked", "comment",
]
DEFAULT_OUT = ROOT / "eval" / "dataset" / "real_labels.csv"


def _setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def _rel(p: Path) -> str:
    try:
        return p.resolve().relative_to(ROOT).as_posix()
    except ValueError:
        return p.resolve().as_posix()


def read_sheet(path: Path) -> list[dict[str, str]]:
    if not path.is_file():
        return []
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "cp1256"):  # Excel on Arabic Windows may save as cp1256
        try:
            text = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw.decode("utf-8", errors="replace")
    return [dict(r) for r in csv.DictReader(text.splitlines())]


def write_sheet(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # utf-8-sig so Excel shows Arabic correctly when opening the file
    with open(path, "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=COLUMNS, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({c: r.get(c, "") for c in COLUMNS})


def main(argv: Optional[list[str]] = None) -> int:
    _setup_console()
    ap = argparse.ArgumentParser(description="Create/extend the labelling sheet for real recordings")
    ap.add_argument("--audio-dir", default=str(ROOT / "eval" / "audio" / "collected"),
                    help="folder with recordings; one sub-folder per speaker is recommended")
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    ap.add_argument("--prefill", action="store_true", help="pre-fill with the app's guesses (faster, but biased)")
    args = ap.parse_args(argv)

    audio_dir = Path(args.audio_dir)
    if not audio_dir.is_dir():
        audio_dir.mkdir(parents=True, exist_ok=True)
        print(f"Created {audio_dir}. Put the recordings there (one sub-folder per speaker), then run this again.")
        return 0
    files = sorted(p for p in audio_dir.rglob("*") if p.is_file() and p.suffix.lower() in SUPPORTED_EXTENSIONS)
    out = Path(args.out)
    rows = read_sheet(out)
    known = {r.get("file", "") for r in rows}
    tz = get_timezone()
    added = 0
    for f in files:
        rel = _rel(f)
        if rel in known:
            continue
        speaker = f.parent.name if f.parent != audio_dir else "unknown"
        mtime = datetime.fromtimestamp(f.stat().st_mtime, tz).replace(second=0, microsecond=0)
        row: dict[str, Any] = {"file": rel, "speaker": speaker, "reference_time": mtime.strftime("%Y-%m-%d %H:%M"),
                               "transaction_type": "expense", "currency": "EGP", "payment_method": "unknown"}
        if args.prefill:
            from voice_expense.asr import AudioValidationError
            from voice_expense.pipeline import process_audio

            try:
                d = process_audio(f, now=mtime, extractor="rules")
                row.update({"transcript": d.transcript, "lang_group": d.language,
                            "transaction_type": d.transaction_type,
                            "amount": "" if d.amount is None else f"{d.amount}", "currency": d.currency,
                            "merchant": d.merchant or "", "category": d.category, "date": d.date.isoformat(),
                            "time": d.time or "", "payment_method": d.payment_method,
                            "comment": "PREFILLED - check every field"})
            except AudioValidationError as exc:
                row["comment"] = f"could not read audio: {exc.message}"
        rows.append(row)
        added += 1
        print(f"  + {rel}")
    write_sheet(out, rows)
    print(f"\n{added} new rows, {len(rows)} total → {out}")
    print("Open it in Excel, fill every row (rules: docs/REAL_DATASET.md), set checked=yes, "
          "save as 'CSV UTF-8', then run:  python eval/import_labels.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
