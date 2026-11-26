"""Stage-2 interface and the structured output record.

Every extractor returns, per message, the same JSON-ready dict. A field the SMS
does not contain is None (JSON null) — never guessed, never "".

    {
      "amount": 250.0,               float
      "currency": "EGP",             ISO code
      "direction": "debit",          "debit" | "credit" | null (derived from type)
      "type": "debit",               v1's type: debit, credit, transfer_out,
                                     transfer_in, atm_withdrawal, bill_payment, other
      "channel": "card",
      "counterparty": "CARREFOUR",   merchant / recipient / sender (v1's `merchant`)
      "date": "2026-08-10",          date part of datetime
      "datetime": "2026-08-10T15:49:00",   or just a date when no time is given
      "account_last4": "4321",
      "fee": null,
      "balance_after": 1234.5,
      "reference": "IP2601045307672" rule-based, NOT evaluated (no gold labels)
      "extraction_ok": true,         false when no amount could be found
      "extraction_note": null
    }

`to_v1(record)` converts back to v1's schema (merchant instead of counterparty),
which is what the corpus's gold `expected` uses and what evaluation compares.
"""
import re

# type -> direction of money for the account holder
DIRECTION = {"debit": "debit", "transfer_out": "debit", "atm_withdrawal": "debit",
             "bill_payment": "debit", "credit": "credit", "transfer_in": "credit",
             "other": None, None: None}

V1_FIELDS = ["type", "amount", "currency", "fee", "balance_after", "merchant",
             "channel", "datetime", "account_last4"]

OUTPUT_FIELDS = ["amount", "currency", "direction", "type", "channel", "counterparty",
                 "date", "datetime", "account_last4", "fee", "balance_after", "reference"]

# Reference / transaction id. Cue word, optional punctuation, then an id that
# contains at least 6 characters and at least one digit.
_REF = re.compile(
    r"(?:\bref(?:erence)?(?:\s*(?:no|number|#))?|\btxn(?:\s*id)?|\btransaction\s*id|"
    r"رقم العملية|رقم العمليه|رقم الحركة|رقم المرجع|المرجع)"
    r"\s*[:.#]?\s*(?=[A-Za-z0-9-]*\d)([A-Za-z0-9][A-Za-z0-9-]{5,})", re.I)


def find_reference(normalized_text):
    m = _REF.search(normalized_text or "")
    return m.group(1) if m else None


def empty_output(note=None):
    out = {k: None for k in OUTPUT_FIELDS}
    out.update(extraction_ok=False, extraction_note=note)
    return out


def from_v1(pred, normalized_text):
    """v1-schema prediction -> output record. Values are carried over, not changed."""
    if not pred.get("is_transaction") or pred.get("amount") is None:
        return empty_output(pred.get("_reason") or "no amount found")
    dt_ = pred.get("datetime")
    return {"amount": pred.get("amount"), "currency": pred.get("currency"),
            "direction": DIRECTION.get(pred.get("type")), "type": pred.get("type"),
            "channel": pred.get("channel"), "counterparty": pred.get("merchant"),
            "date": dt_[:10] if dt_ else None, "datetime": dt_,
            "account_last4": pred.get("account_last4"), "fee": pred.get("fee"),
            "balance_after": pred.get("balance_after"),
            "reference": find_reference(normalized_text),
            "extraction_ok": True, "extraction_note": None}


def to_v1(rec):
    """Output record -> v1 schema (is_transaction + V1_FIELDS)."""
    if rec is None or not rec.get("extraction_ok"):
        out = {k: None for k in V1_FIELDS}
        out["is_transaction"] = False
        return out
    out = {k: rec.get(k) for k in V1_FIELDS if k != "merchant"}
    out["merchant"] = rec.get("counterparty")
    out["is_transaction"] = True
    return out


class BaseExtractor:
    name = "base"

    def fit(self, train_records):
        return self

    def extract_many(self, texts):
        """-> list of output records (see module docstring)."""
        raise NotImplementedError

    def extract(self, text):
        return self.extract_many([text])[0]

    def save(self, directory):
        raise NotImplementedError

    @classmethod
    def load(cls, directory):
        raise NotImplementedError
