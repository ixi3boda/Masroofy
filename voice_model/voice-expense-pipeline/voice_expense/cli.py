"""Command-line interface.

Examples:
    python -m voice_expense.cli text "صرفت 250 على groceries امبارح" --now 2026-11-20T14:00
    python -m voice_expense.cli audio path/to/file.wav --asr-backend faster_whisper
    python -m voice_expense.cli interactive
    python -m voice_expense.cli list

WHY a CLI: it is the fastest way for a teammate to try a sentence, and it
shows exactly what the mobile app will receive (the JSON draft).
"""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any, Optional

from .asr import AudioValidationError
from .categories import category_labels
from .config import get_settings
from .pipeline import process_audio, process_text
from .schemas import EDITABLE_FIELDS, ConfirmRequest, ExpenseDraft
from .storage import list_transactions, save_confirmed


def _setup_console() -> None:
    """Make Arabic print correctly on Windows consoles (cp1252/cp437 by default)."""
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
        except Exception:
            pass


def _summary(d: ExpenseDraft) -> str:
    labels = category_labels()
    amount = f"{d.amount} {d.currency}" if d.amount is not None else "?? (no amount found)"
    lines = [
        f"{'Income' if d.transaction_type == 'income' else 'Expense'} / {'دخل' if d.transaction_type == 'income' else 'مصروف'}: {amount}",
        f"Merchant / التاجر: {d.merchant or '-'}",
        f"Category / الفئة: {labels.get(d.category, d.category)}",
        f"Date / التاريخ: {d.date}{(' ' + d.time) if d.time else ''}",
        f"Payment / الدفع: {d.payment_method}",
    ]
    if d.note:
        lines.append(f"Note / ملاحظة: {d.note}")
    if d.needs_review:
        lines.append(f"Please check / راجع: {', '.join(d.needs_review)}")
    for w in d.warnings:
        lines.append(f"Warning: {w}")
    t = d.timings_ms
    lines.append(f"Timings (ms): asr={t.asr} normalize={t.normalize} extract={t.extract} total={t.total}"
                 + (f" model_load={t.model_load}" if t.model_load else ""))
    return "\n".join(lines)


def _print_draft(d: ExpenseDraft) -> None:
    print(json.dumps(d.model_dump(mode="json"), ensure_ascii=False, indent=2))
    print()
    print(_summary(d))


def _common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--now", help="reference time, e.g. 2026-11-20T14:00 (Africa/Cairo if no offset)")
    p.add_argument("--extractor", choices=["rules", "llm", "hybrid"], help="extraction mode")
    p.add_argument("--asr-backend", choices=["auto", "faster_whisper", "openai_whisper", "openai_api", "mock"])
    p.add_argument("--language", choices=["ar", "en", "auto"], help="ASR language")
    p.add_argument("--db", help="SQLite file (default from DB_PATH)")


def _parse_value(field: str, raw: str) -> Any:
    raw = raw.strip()
    if raw.lower() in ("", "null", "none", "-"):
        return None
    if field == "amount":
        return raw.replace(",", "")
    return raw


def _interactive(args: argparse.Namespace) -> int:
    print("Type an expense sentence, or the path of an audio file. Empty line or 'q' to quit.")
    print("After the draft: press Enter to save, type field=value to edit (e.g. amount=200), or 'x' to discard.")
    while True:
        try:
            line = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        if line in ("", "q", "quit", "exit"):
            return 0
        try:
            if line.lower().endswith((".wav", ".mp3", ".m4a", ".ogg", ".webm", ".flac")):
                draft = process_audio(line, now=args.now, language=args.language, extractor=args.extractor,
                                      asr_backend=args.asr_backend)
            else:
                draft = process_text(line, now=args.now, extractor=args.extractor)
        except AudioValidationError as exc:
            print(f"Error: {exc.message}")
            continue
        _print_draft(draft)
        corrections: dict[str, Any] = {}
        while True:
            try:
                cmd = input("edit> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                return 0
            if cmd == "":
                break
            if cmd.lower() == "x":
                corrections = {"__discard__": True}
                break
            if "=" not in cmd:
                print(f"Use field=value. Fields: {', '.join(EDITABLE_FIELDS)}")
                continue
            k, v = cmd.split("=", 1)
            k = k.strip()
            if k not in EDITABLE_FIELDS:
                print(f"Unknown field '{k}'. Fields: {', '.join(EDITABLE_FIELDS)}")
                continue
            corrections[k] = _parse_value(k, v)
            print(f"  {k} -> {corrections[k]}")
        if corrections.get("__discard__"):
            print("Discarded.")
            continue
        try:
            saved = save_confirmed(ConfirmRequest(draft=draft, corrections=corrections), db_path=args.db)
        except ValueError as exc:
            msg = "An amount is required. Type amount=... next time." if str(exc) == "amount_required" else str(exc)
            print(f"Not saved: {msg}")
            continue
        print("Saved:")
        print(json.dumps(saved.model_dump(mode="json", include={"id", "created_at", "amount", "currency", "merchant",
                                                               "category", "date", "time", "payment_method", "note",
                                                               "user_edited_fields"}), ensure_ascii=False, indent=2))


def main(argv: Optional[list[str]] = None) -> int:
    _setup_console()
    parser = argparse.ArgumentParser(prog="python -m voice_expense.cli", description="Voice expense pipeline CLI")
    sub = parser.add_subparsers(dest="command")

    p_text = sub.add_parser("text", help="parse a typed sentence")
    p_text.add_argument("sentence")
    _common(p_text)
    p_audio = sub.add_parser("audio", help="transcribe and parse an audio file")
    p_audio.add_argument("path")
    _common(p_audio)
    p_int = sub.add_parser("interactive", help="type/record, review, edit and save in a loop")
    _common(p_int)
    p_list = sub.add_parser("list", help="show saved transactions")
    p_list.add_argument("--limit", type=int, default=20)
    p_list.add_argument("--db", help="SQLite file (default from DB_PATH)")

    args = parser.parse_args(argv)
    if args.command is None:
        parser.print_help()
        return 1
    get_settings()
    if args.command == "text":
        _print_draft(process_text(args.sentence, now=args.now, extractor=args.extractor))
        return 0
    if args.command == "audio":
        try:
            draft = process_audio(args.path, now=args.now, language=args.language, extractor=args.extractor,
                                  asr_backend=args.asr_backend)
        except AudioValidationError as exc:
            print(f"Error ({exc.error_code}): {exc.message}", file=sys.stderr)
            return 2
        _print_draft(draft)
        return 0
    if args.command == "interactive":
        return _interactive(args)
    if args.command == "list":
        rows = list_transactions(limit=args.limit, db_path=args.db)
        if not rows:
            print("No saved transactions yet. Use: python -m voice_expense.cli interactive")
            return 0
        for r in rows:
            edited = f" (edited: {', '.join(r.user_edited_fields)})" if r.user_edited_fields else ""
            print(f"#{r.id} {r.date} {r.amount} {r.currency} | {r.merchant or '-'} | {r.category} | "
                  f"{r.payment_method}{edited}")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
