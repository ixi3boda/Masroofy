"""SQLite storage for confirmed transactions and user corrections.

WHY SQLite: it is built into Python (no server to install), it is one file,
and it is enough for a demo and for measuring correction rates. The mobile
app's real backend can replace this module later; the API contract stays the same.

WHY store corrections separately: the proposal asks "how often users need to
correct a field". Every confirm call records which fields the user changed,
so `correction_stats()` can answer that from real usage.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Optional

from .config import get_settings, get_timezone
from .schemas import EDITABLE_FIELDS, ConfirmedTransaction, ConfirmRequest, ExpenseDraft

_LOCK = threading.Lock()

_SCHEMA = """
CREATE TABLE IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    transaction_type TEXT NOT NULL,
    amount TEXT,
    currency TEXT NOT NULL,
    merchant TEXT,
    category TEXT NOT NULL,
    date TEXT NOT NULL,
    time TEXT,
    payment_method TEXT NOT NULL,
    note TEXT,
    language TEXT,
    transcript TEXT,
    extraction_method TEXT,
    user_edited_fields TEXT NOT NULL,
    draft_json TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS corrections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transaction_id INTEGER NOT NULL REFERENCES transactions(id),
    field TEXT NOT NULL,
    old_value TEXT,
    new_value TEXT,
    created_at TEXT NOT NULL
);
"""


def _db_path(db_path: Optional[str] = None) -> str:
    return db_path or get_settings().db_path


def connect(db_path: Optional[str] = None) -> sqlite3.Connection:
    path = _db_path(db_path)
    if path != ":memory:":
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(_SCHEMA)
    return conn


def _to_text(v: Any) -> Optional[str]:
    if v is None:
        return None
    if isinstance(v, (date, datetime)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return f"{v:.2f}"
    return str(v)


def apply_corrections(draft: ExpenseDraft, corrections: dict[str, Any]) -> tuple[ExpenseDraft, list[str]]:
    """Return the corrected draft (validated again) and the list of fields that really changed."""
    data = draft.model_dump()
    for k, new in corrections.items():
        if k in EDITABLE_FIELDS:
            data[k] = new
    final = ExpenseDraft.model_validate(data)
    # Compare AFTER validation so "150" vs 150.00 does not count as a correction.
    really = [k for k in corrections
              if k in EDITABLE_FIELDS and _to_text(getattr(final, k)) != _to_text(getattr(draft, k))]
    final.needs_review = [f for f in final.needs_review if f not in corrections]
    return final, really


def save_confirmed(req: ConfirmRequest, db_path: Optional[str] = None) -> ConfirmedTransaction:
    """Apply corrections, save the transaction and its corrections, return the saved record."""
    final, edited = apply_corrections(req.draft, req.corrections)
    if final.amount is None:
        raise ValueError("amount_required")
    now = datetime.now(get_timezone(get_settings().timezone_name)).replace(microsecond=0)
    with _LOCK:
        conn = connect(db_path)
        try:
            cur = conn.execute(
                """INSERT INTO transactions (created_at, transaction_type, amount, currency, merchant, category,
                       date, time, payment_method, note, language, transcript, extraction_method,
                       user_edited_fields, draft_json)
                   VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    now.isoformat(), final.transaction_type, _to_text(final.amount), final.currency, final.merchant,
                    final.category, final.date.isoformat(), final.time, final.payment_method, final.note,
                    final.language, final.transcript, final.extraction_method, json.dumps(edited),
                    req.draft.model_dump_json(),
                ),
            )
            tx_id = int(cur.lastrowid or 0)
            for k in edited:
                conn.execute(
                    "INSERT INTO corrections (transaction_id, field, old_value, new_value, created_at) VALUES (?,?,?,?,?)",
                    (tx_id, k, _to_text(getattr(req.draft, k)), _to_text(getattr(final, k)), now.isoformat()),
                )
            conn.commit()
        finally:
            conn.close()
    data = final.model_dump()
    data.update({"id": tx_id, "created_at": now, "user_edited_fields": edited})
    return ConfirmedTransaction.model_validate(data)


def _row_to_tx(row: sqlite3.Row) -> ConfirmedTransaction:
    draft = json.loads(row["draft_json"])
    draft.update({
        "transaction_type": row["transaction_type"],
        "amount": row["amount"],
        "currency": row["currency"],
        "merchant": row["merchant"],
        "category": row["category"],
        "date": row["date"],
        "time": row["time"],
        "payment_method": row["payment_method"],
        "note": row["note"],
        "id": row["id"],
        "created_at": row["created_at"],
        "user_edited_fields": json.loads(row["user_edited_fields"]),
    })
    draft["needs_review"] = []
    return ConfirmedTransaction.model_validate(draft)


def list_transactions(limit: int = 100, db_path: Optional[str] = None) -> list[ConfirmedTransaction]:
    with _LOCK:
        conn = connect(db_path)
        try:
            rows = conn.execute("SELECT * FROM transactions ORDER BY id DESC LIMIT ?", (int(limit),)).fetchall()
        finally:
            conn.close()
    return [_row_to_tx(r) for r in rows]


def correction_stats(db_path: Optional[str] = None) -> dict[str, Any]:
    """Real-usage correction rate: per-field counts and % of transactions with at least one fix."""
    with _LOCK:
        conn = connect(db_path)
        try:
            total = conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0]
            with_fix = conn.execute("SELECT COUNT(*) FROM transactions WHERE user_edited_fields != '[]'").fetchone()[0]
            per_field = {r[0]: r[1] for r in conn.execute("SELECT field, COUNT(*) FROM corrections GROUP BY field")}
        finally:
            conn.close()
    fixes = sum(per_field.values())
    return {
        "transactions": total,
        "with_at_least_one_correction": with_fix,
        "pct_with_correction": round(100.0 * with_fix / total, 1) if total else 0.0,
        "avg_fields_corrected": round(fixes / total, 3) if total else 0.0,
        "per_field": per_field,
    }
