"""Accuracy on REAL usage: compare what the app proposed with what the user confirmed.

    python eval/confirmed_report.py                 # uses DB_PATH (default expenses.db)
    python eval/confirmed_report.py --db expenses.db --since 2026-11-01

WHY: every time someone presses "Confirm" (Gradio demo, CLI interactive mode or
POST /v1/expenses/confirm) we store BOTH the original draft and the final values.
If we treat the confirmed values as the correct answer ("ground truth") and the draft
as the prediction, we can compute the same metrics as eval/evaluate.py on real users'
real sentences — no hand labelling needed:
    * per-field accuracy, precision, recall, F1 (by language and by input type voice/text)
    * correction rate = how often users had to fix a field (the proposal's metric)
    * whether the ⚠️ highlight pointed at the fields users actually fixed
    * latency of the drafts that were confirmed

Caveat (write it in your report): a field the user did NOT change is counted as correct.
If a user saves without checking, mistakes are counted as correct, so these numbers are
an upper bound. Ask testers to always fix wrong fields before pressing Confirm.
"""
from __future__ import annotations

import argparse
import csv
import json
import sqlite3
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from eval.evaluate import _na, _prf_section, _setup_console, _table, write_confusion  # noqa: E402
from eval.metrics import EVAL_FIELDS, aggregate, latency_stats, score_record  # noqa: E402
from voice_expense.config import get_settings  # noqa: E402


def _amount(v: Any) -> Optional[float]:
    if v in (None, ""):
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def load_records(db_path: str, since: Optional[str] = None) -> list[dict[str, Any]]:
    """One record per confirmed transaction: predicted = original draft, expected = confirmed values."""
    if not Path(db_path).is_file():
        return []
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute("SELECT * FROM transactions ORDER BY id").fetchall()
    finally:
        conn.close()
    records = []
    for row in rows:
        if since and str(row["created_at"])[:10] < since:
            continue
        draft = json.loads(row["draft_json"])
        expected = {
            "transaction_type": row["transaction_type"], "amount": _amount(row["amount"]),
            "currency": row["currency"], "merchant": row["merchant"], "category": row["category"],
            "date": row["date"], "time": row["time"], "payment_method": row["payment_method"],
        }
        predicted = {
            "transaction_type": draft.get("transaction_type"), "amount": _amount(draft.get("amount")),
            "currency": draft.get("currency"), "merchant": draft.get("merchant"), "category": draft.get("category"),
            "date": str(draft.get("date")), "time": draft.get("time"), "payment_method": draft.get("payment_method"),
        }
        timings = draft.get("timings_ms") or {}
        input_type = "voice" if float(timings.get("asr") or 0) > 0 else "text"
        records.append({
            "id": row["id"],
            "created_at": row["created_at"],
            "lang_group": draft.get("language") or "unknown",
            "difficulty": "n/a",
            "input_type": input_type,
            "method": draft.get("extraction_method"),
            "transcript": draft.get("transcript", ""),
            "expected": expected,
            "predicted": predicted,
            "correct": score_record(expected, predicted, []),
            "needs_review": draft.get("needs_review", []),
            "edited": json.loads(row["user_edited_fields"]),
            "total_ms": float(timings.get("total") or 0),
            "asr_ms": float(timings.get("asr") or 0),
        })
    return records


def build_report(records: list[dict[str, Any]], db_path: str) -> tuple[str, dict[str, Any]]:
    agg = aggregate(records)
    by_input = {t: aggregate([r for r in records if r["input_type"] == t])
                for t in ("voice", "text") if any(r["input_type"] == t for r in records)}
    counts = ", ".join(f"{t}: {sum(r['input_type'] == t for r in records)}" for t in ("voice", "text"))
    md = ["# Accuracy on confirmed transactions (real usage)", "",
          f"Database: `{db_path}` · transactions: **{len(records)}** ({counts}) · "
          f"generated {datetime.now().isoformat(timespec='seconds')}", "",
          "Ground truth = the values the user confirmed; prediction = the draft the app proposed. A field the user "
          "did not change counts as correct, so these numbers are an upper bound if users saved without checking.", ""]
    if len(records) < 30:
        md.append(f"> ⚠️ Only {len(records)} transactions — percentages will swing a lot. Aim for 50+ per language.\n")
    md.append(_table("Per-field accuracy (%) — all", {"all": agg["field_accuracy"]}, EVAL_FIELDS))
    md.append(_table("Per-field accuracy (%) — by language", agg["by_lang"], EVAL_FIELDS))
    md.append(_table("Per-field accuracy (%) — voice vs typed", {t: a["field_accuracy"] for t, a in by_input.items()},
                     EVAL_FIELDS))
    md.append(f"**Full-record exact match** (amount, currency, merchant, category, date): **{agg['exact_match']}%**\n")
    md.append("**Correction rate (the proposal's \"how often users need to correct a field\")**\n")
    md.append("| group | avg fields corrected per transaction | % transactions with ≥1 correction |\n|---|---|---|")
    md.append(f"| all | {agg['correction']['avg_fields_to_fix']} | {agg['correction']['pct_needing_fix']} |")
    for g, c in agg["correction_by_lang"].items():
        md.append(f"| {g} | {c['avg_fields_to_fix']} | {c['pct_needing_fix']} |")
    for t, a in by_input.items():
        md.append(f"| {t} | {a['correction']['avg_fields_to_fix']} | {a['correction']['pct_needing_fix']} |")
    md.append("")
    md.append(f"**⚠️ highlight quality**: precision {_na(agg['review_precision'])}% (highlighted fields the user really "
              f"fixed), recall {_na(agg['review_recall'])}% (fixed fields that were highlighted), "
              f"F1 {_na(agg['review_f1'])}%.\n")
    md.extend(_prf_section(agg))
    lat = latency_stats([r["total_ms"] for r in records])
    asr = latency_stats([r["asr_ms"] for r in records if r["asr_ms"] > 0])
    md.append("**Latency of confirmed drafts (ms)**\n")
    md.append("| stage | mean | p50 | p95 | n |\n|---|---|---|---|---|")
    md.append(f"| total | {lat['mean']} | {lat['p50']} | {lat['p95']} | {lat['n']} |")
    if asr["n"]:
        md.append(f"| asr (voice only) | {asr['mean']} | {asr['p50']} | {asr['p95']} | {asr['n']} |")
    md.append("")
    return "\n".join(md) + "\n", agg


def main(argv: Optional[list[str]] = None) -> int:
    _setup_console()
    ap = argparse.ArgumentParser(description="Accuracy of drafts vs what users confirmed")
    ap.add_argument("--db", default=None, help="SQLite file (default: DB_PATH setting, expenses.db)")
    ap.add_argument("--since", default=None, help="only transactions created on/after this date (YYYY-MM-DD)")
    ap.add_argument("--out", default=str(ROOT / "results"))
    args = ap.parse_args(argv)

    db_path = args.db or get_settings().db_path
    records = load_records(db_path, args.since)
    if not records:
        print(f"No confirmed transactions found in {db_path}.\n"
              "Confirm some drafts first (python -m voice_expense.gradio_app, or the CLI 'interactive' mode), "
              "or pass --db with the right file.")
        return 1
    out_dir = Path(args.out) / f"confirmed-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)
    report, agg = build_report(records, db_path)
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    write_confusion(out_dir, agg)
    with open(out_dir / "transactions.csv", "w", encoding="utf-8-sig", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["id", "created_at", "input_type", "language", "method", "transcript", "edited_fields"]
                   + [f"{p}_{f}" for f in EVAL_FIELDS for p in ("draft", "confirmed")])
        for r in records:
            w.writerow([r["id"], r["created_at"], r["input_type"], r["lang_group"], r["method"], r["transcript"],
                        "|".join(r["edited"])]
                       + [v for f in EVAL_FIELDS for v in (r["predicted"][f], r["expected"][f])])

    print(f"{len(records)} confirmed transactions in {db_path}")
    print("accuracy %: " + ", ".join(f"{f}={agg['field_accuracy'][f]}" for f in EVAL_FIELDS))
    m = agg["slot_prf"]["micro"]
    print(f"all fields: precision {_na(m['precision'])}%  recall {_na(m['recall'])}%  F1 {_na(m['f1'])}%")
    print(f"exact match {agg['exact_match']}% | avg fields corrected {agg['correction']['avg_fields_to_fix']} | "
          f"transactions with a correction {agg['correction']['pct_needing_fix']}%")
    if len(records) < 30:
        print(f"Note: only {len(records)} transactions; collect more for reliable numbers.")
    print(f"Report: {out_dir / 'report.md'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
