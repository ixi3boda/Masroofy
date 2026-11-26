"""The record schema, shared by v1 and v2 so the two are directly comparable.

Field names, value conventions and the ISO datetime format are exactly those of
sms_eval_final/sms_model.py, because sms_eval_final/evaluate.py:score() is what
compare.py uses to grade both implementations.
"""

# Graded fields, in evaluate.py's order.
FIELDS = ["type", "amount", "currency", "fee", "balance_after",
          "merchant", "channel", "datetime", "account_last4"]

# v1 folds "not a transaction" into the type label as "none"; v2 has a separate
# gate, so the extractor only ever sees the seven real types.
TYPES_V1 = ["none", "debit", "credit", "transfer_out", "transfer_in",
            "atm_withdrawal", "bill_payment", "other"]
TYPES = TYPES_V1[1:]

CHANNELS = ["card", "instapay", "wallet", "bank_transfer", "atm", "other", "unknown"]

# Token-tagged fields. DATE and TIME are tagged separately and recombined into
# the single `datetime` field at decode time, because the two are usually far
# apart in the text ("... يوم 10/08/26 الساعة 15:49").
SPAN_TAGS = ["AMOUNT", "FEE", "BALANCE", "LAST4", "MERCHANT", "CURRENCY", "DATE", "TIME"]

# BIO label set for the token head: O + B-/I- per tag.
TOKEN_LABELS = ["O"] + [f"{p}-{t}" for t in SPAN_TAGS for p in ("B", "I")]
TOKEN_LABEL_ID = {l: i for i, l in enumerate(TOKEN_LABELS)}

IGNORE_INDEX = -100          # torch CrossEntropyLoss default


def empty_record():
    """A prediction with every field unset — the shape v1's predict() returns."""
    return {"is_transaction": False, "type": None, "amount": None, "currency": None,
            "fee": None, "balance_after": None, "merchant": None, "channel": None,
            "datetime": None, "account_last4": None}
