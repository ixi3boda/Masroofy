"""Stage-1 label definitions — the ONE place to change what the classes mean.

Nothing in here is learned. It turns the corpus's existing annotations into the
two label sets the benchmark uses, and every decision is written down so it can be
audited (`python bench.py prepare` writes data/processed/label_audit.csv with the
class and the reason for every single message).

Where the labels come from
--------------------------
The corpus (sms_eval_final/sms_dataset_2200.jsonl) carries exactly one gold
classification label: `expected.is_transaction`. The manifest
(sms_eval_final/manifest_2200.csv) adds a `category` per message, written by the
data generator. So:

  * Experiment A (binary) uses `is_transaction` directly. No mapping, no rules.
  * Experiment B (multi-class) needs finer non-transaction classes, which the
    corpus does NOT have. They are derived from `category`:
      - CATEGORY_MAP: categories that are homogeneous (checked by reading them)
        map straight to a class;
      - MIXED_CATEGORIES: four real-format buckets ("cib_none", "hsbc_none",
        "bm_none", "oc_none") mix OTPs, declines, promos and alerts in one category,
        so each message in them is classified by the ordered keyword RULES below.
    Every gold transaction (`is_transaction == True`) is "transaction", whatever
    its category; a category that maps to a non-transaction class but contains a
    gold transaction is a hard error, not a silent relabel.

So Experiment B's non-transaction sub-classes are DERIVED labels, not
human-annotated ones. That is a stated limitation of the benchmark.
"""

# --------------------------------------------------------------------- classes
# Order matters only for display; "transaction" must stay the routing class.
CLASSES = {
    "transaction": "Successful financial transaction: purchase, payment, transfer in/out, "
                   "deposit, withdrawal, refund or reversal that actually moved money.",
    "balance_inquiry": "Balance / available-limit notification with no new transaction.",
    "otp": "Verification codes, one-time passwords, PINs to confirm an action.",
    "promotional": "Marketing, offers, cashback campaigns, loan / instalment offers.",
    "failed_transaction": "Declined, rejected, failed or insufficient-funds attempts. "
                          "No money moved, so no financial record.",
    "other": "Everything else: due-date reminders and statements, security / login "
             "alerts, phishing, dormancy notices, pending requests awaiting "
             "confirmation, pending refunds.",
}

# The class that proceeds to Stage 2. Business rule: ONLY this one.
TRANSACTION = "transaction"

# Binary experiment label names.
BINARY_CLASSES = ["transaction", "non_transaction"]
NON_TRANSACTION = "non_transaction"

# --------------------------------------------------------------------- mapping
# Homogeneous non-transaction categories -> class. Each was verified by reading
# samples (see AUDIT.md). Categories not listed here and not in MIXED_CATEGORIES
# are transaction categories; a non-transaction message in an unlisted category
# raises an error so a new category can never be silently mislabelled.
CATEGORY_MAP = {
    "otp": "otp",
    "instapay_none": "otp",               # InstaPay app activation codes
    "promo": "promotional",
    "vf_promo": "promotional",
    "declined": "failed_transaction",
    "vf_insufficient": "failed_transaction",
    "vf_wrong_pin": "failed_transaction",
    "balance": "balance_inquiry",
    "vf_balance": "balance_inquiry",
    "due": "other",                       # instalment / bill due reminders, statements
    "valu_none": "other",                 # valU instalment reminders
    "security": "other",
    "phishing": "other",
    "nbe_dormancy": "other",
    "vf_withdraw_request": "other",       # cash-out REQUESTED, awaiting PIN confirmation
}

# Real-format buckets that mix several kinds of message; resolved per message.
MIXED_CATEGORIES = {"cib_none", "hsbc_none", "bm_none", "oc_none"}

# Ordered (class, regex) rules for MIXED_CATEGORIES, applied to the normalized
# text (Arabic-Indic digits already ASCII). First match wins; no match -> "other".
# Order is deliberate: a decline that mentions the balance is a decline, an OTP
# that mentions an amount is an OTP.
RULES = [
    ("failed_transaction",
     r"رفض|تعذر|فشل|لم يتم|غير كاف|declined|not successful|unsuccessful|failed|"
     r"could not|insufficient"),
    ("otp",
     r"\bOTP\b|الرقم السري المتغير|كود التأكيد|كود التحقق|رمز التحقق|كود التفعيل|"
     r"one[- ]time|verification code|\bUse PIN\b|\bPIN \d{4,}|passcode"),
    ("promotional",
     r"احصل|عرض|كاش ?باك|cashback|offer|ادفع فواتيرك|حوّل لأي|حول لأي|اشحن|قسط مشترياتك|"
     r"قسّط|استمتع|enjoy|exclusive|discount|خصم \d+ ?%|\d+ ?% "),
    ("balance_inquiry",
     r"رصيد[^.\n]{0,30}?(?:الحالي|المتاح)|available balance|balance is|current balance"),
]
