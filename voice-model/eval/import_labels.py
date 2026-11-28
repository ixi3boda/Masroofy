"""Step 2 of the REAL dataset: check the labelled sheet and turn it into an evaluation dataset.

    python eval/import_labels.py
    python eval/import_labels.py --sheet eval/dataset/real_labels.csv --skip-invalid

Reads eval/dataset/real_labels.csv (filled in Excel) and writes:
    eval/dataset/real.jsonl         labels in the same format as phrases.jsonl
    eval/dataset/real_manifest.csv  audio file list for the audio evaluation

Every row is validated (category must be a known id, dates must be real dates, the
audio file must exist ...). Problems are printed with the row number so you can fix
them in Excel. Only rows with checked=yes are imported.

Then evaluate:
    python eval/evaluate.py --mode audio --dataset eval/dataset/real.jsonl --manifest eval/dataset/real_manifest.csv
    python eval/evaluate.py --mode text  --dataset eval/dataset/real.jsonl      # extraction only (human transcripts)
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.make_label_sheet import DEFAULT_OUT, read_sheet  # noqa: E402
from voice_expense.categories import category_ids  # noqa: E402
from voice_expense.config import resolve_now  # noqa: E402
from voice_expense.merchants import get_gazetteer  # noqa: E402

LANG_GROUPS = {"ar", "en", "mixed", "franco"}
PAYMENTS = {"cash", "card", "wallet", "unknown"}
YES = {"yes", "y", "1", "true", "نعم", "ايوه", "اه", "✓"}


def _setup_console() -> None:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def parse_date(text: str) -> date:
    """Accept 2026-11-20, 20/11/2026, 20-11-2026 (Excel on Egyptian Windows shows day/month/year)."""
    t = text.strip()
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})", t)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})", t)
    if m:
        return date(int(m.group(3)), int(m.group(2)), int(m.group(1)))
    raise ValueError(f"date '{text}' must be YYYY-MM-DD (or DD/MM/YYYY)")


def parse_reference(text: str) -> datetime:
    """When the note was recorded: 2026-11-25 18:30, 2026-11-25T18:30, or Excel's 25/11/2026 18:30."""
    t = text.strip()
    m = re.fullmatch(r"(\d{1,2})[/\-.](\d{1,2})[/\-.](\d{4})(?:[ T](\d{1,2}):(\d{2})(?::\d{2})?)?", t)
    if m:
        dt = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)), int(m.group(4) or 12), int(m.group(5) or 0))
        return resolve_now(dt)
    t = re.sub(r"^(\d{4})/(\d{1,2})/(\d{1,2})", r"\1-\2-\3", t)
    m = re.fullmatch(r"(\d{4})-(\d{1,2})-(\d{1,2})$", t)
    if m:  # date only -> assume noon
        return resolve_now(datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)), 12, 0))
    try:
        return resolve_now(datetime.fromisoformat(t))
    except ValueError:
        raise ValueError(f"reference_time '{text}' must look like 2026-11-25 18:30")


def parse_time(text: str) -> Optional[str]:
    t = text.strip().lower()
    if not t:
        return None
    m = re.fullmatch(r"(\d{1,2}):(\d{2})(?::\d{2})?\s*(am|pm|ص|م)?", t)
    if not m:
        raise ValueError(f"time '{text}' must be HH:MM (24h), e.g. 19:30")
    h, mi = int(m.group(1)), int(m.group(2))
    if m.group(3) in ("pm", "م") and h < 12:
        h += 12
    if m.group(3) in ("am", "ص") and h == 12:
        h = 0
    if not (0 <= h <= 23 and 0 <= mi <= 59):
        raise ValueError(f"time '{text}' is not a valid time")
    return f"{h:02d}:{mi:02d}"


def parse_amount(text: str) -> Optional[float]:
    t = text.strip().replace(",", "").replace("٬", "")
    if not t:
        return None
    try:
        v = Decimal(t)
    except InvalidOperation:
        raise ValueError(f"amount '{text}' is not a number (leave empty if no amount was said)")
    if v <= 0:
        raise ValueError("amount must be positive")
    return float(v)


def convert_row(row: dict[str, str]) -> dict[str, Any]:
    """Validate one sheet row and return a dataset example (raises ValueError with a clear message)."""
    g = lambda k: (row.get(k) or "").strip()  # noqa: E731
    rel = g("file")
    if not rel:
        raise ValueError("file is empty")
    path = Path(rel) if Path(rel).is_absolute() else ROOT / rel
    if not path.is_file():
        raise ValueError(f"audio file not found: {rel}")
    transcript = g("transcript")
    if not transcript:
        raise ValueError("transcript is empty (type exactly what the person said)")
    lang = g("lang_group").lower()
    if lang not in LANG_GROUPS:
        raise ValueError(f"lang_group '{lang}' must be one of {sorted(LANG_GROUPS)}")
    if not g("reference_time"):
        raise ValueError("reference_time is empty (when was it recorded? e.g. 2026-11-25 18:30)")
    ref = parse_reference(g("reference_time"))
    tx = (g("transaction_type") or "expense").lower()
    if tx not in ("expense", "income"):
        raise ValueError("transaction_type must be expense or income")
    currency = (g("currency") or "EGP").upper()
    if not re.fullmatch(r"[A-Z]{3}", currency):
        raise ValueError(f"currency '{currency}' must be a 3-letter code like EGP or USD")
    category = g("category")
    if category not in category_ids():
        raise ValueError(f"category '{category}' must be one of: {', '.join(category_ids())}")
    payment = (g("payment_method") or "unknown").lower()
    if payment not in PAYMENTS:
        raise ValueError(f"payment_method must be one of {sorted(PAYMENTS)}")
    if not g("date"):
        raise ValueError("date is empty (the date of the expense, e.g. the reference date for 'today')")
    d = parse_date(g("date"))
    merchant_raw = g("merchant") or None
    merchant = (get_gazetteer().canonical(merchant_raw) or merchant_raw) if merchant_raw else None
    speaker = g("speaker") or "unknown"
    ex_id = re.sub(r"[^A-Za-z0-9_]+", "_", f"real_{speaker}_{Path(rel).stem}")[:80]
    tags = ["real", f"speaker:{speaker}"]
    if g("time_word").lower() in YES:
        tags.append("time_word")
    return {
        "id": ex_id,
        "text": transcript,
        "lang_group": lang,
        "reference_time": ref.isoformat(),
        "expected": {
            "transaction_type": tx, "amount": parse_amount(g("amount")), "currency": currency,
            "merchant": merchant, "category": category, "date": d.isoformat(), "time": parse_time(g("time")),
            "payment_method": payment,
        },
        "difficulty": "n/a",
        "tags": tags,
        "audio": path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else path.as_posix(),
        "speaker": speaker,
    }


def main(argv: Optional[list[str]] = None) -> int:
    _setup_console()
    ap = argparse.ArgumentParser(description="Validate the labelled sheet and build the real dataset")
    ap.add_argument("--sheet", default=str(DEFAULT_OUT))
    ap.add_argument("--out", default=str(ROOT / "eval" / "dataset" / "real.jsonl"))
    ap.add_argument("--manifest", default=str(ROOT / "eval" / "dataset" / "real_manifest.csv"))
    ap.add_argument("--skip-invalid", action="store_true", help="import the valid rows even if some rows have errors")
    args = ap.parse_args(argv)

    rows = read_sheet(Path(args.sheet))
    if not rows:
        print(f"No rows in {args.sheet}. Run first: python eval/make_label_sheet.py --audio-dir <folder>")
        return 1
    examples, errors, unchecked = [], [], 0
    seen: set[str] = set()
    for i, row in enumerate(rows, start=2):  # line 1 is the header in Excel
        if (row.get("checked") or "").strip().lower() not in YES:
            unchecked += 1
            continue
        try:
            ex = convert_row(row)
        except ValueError as exc:
            errors.append(f"  row {i} ({row.get('file', '')}): {exc}")
            continue
        if ex["id"] in seen:
            errors.append(f"  row {i}: duplicate file/id {ex['id']}")
            continue
        seen.add(ex["id"])
        examples.append(ex)
    if errors:
        print("Problems found (fix them in the sheet):")
        print("\n".join(errors))
        if not args.skip_invalid:
            print(f"\nNothing written. Fix the {len(errors)} rows above, or rerun with --skip-invalid.")
            return 1
    if not examples:
        print(f"No rows marked checked=yes ({unchecked} unchecked). Fill the sheet and set checked=yes on finished rows.")
        return 1
    with open(args.out, "w", encoding="utf-8") as fh:
        for ex in examples:
            fh.write(json.dumps(ex, ensure_ascii=False) + "\n")
    with open(args.manifest, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=["id", "path", "text", "lang_group", "speaker"])
        w.writeheader()
        for ex in examples:
            w.writerow({"id": ex["id"], "path": ex["audio"], "text": ex["text"], "lang_group": ex["lang_group"],
                        "speaker": ex["speaker"]})
    counts: dict[str, int] = {}
    for ex in examples:
        counts[ex["lang_group"]] = counts.get(ex["lang_group"], 0) + 1
    speakers = {ex["speaker"] for ex in examples}
    print(f"Imported {len(examples)} examples from {len(speakers)} speakers: {counts}"
          + (f"  ({unchecked} rows not checked yet, {len(errors)} skipped)" if unchecked or errors else ""))
    for g, n in counts.items():
        if n < 30:
            print(f"  note: only {n} '{g}' examples — aim for 50+ per group for stable numbers")
    print(f"Wrote {args.out} and {args.manifest}\nNext:\n"
          f"  python eval/evaluate.py --mode audio --dataset {args.out} --manifest {args.manifest}\n"
          f"  python eval/evaluate.py --mode text --dataset {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
