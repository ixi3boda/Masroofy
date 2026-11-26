"""Unit tests for the v2 span layer, written as the REAL_FORMATS.md failure list.

    python test_spans.py

Each case names the item in REAL_FORMATS.md "What the real formats break in
SmsTxnModel" that it covers, and asserts v2 gets it right. The v1 column is
printed for contrast, not asserted (v1 is expected to fail these).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spans

V1 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "sms_eval_final")
sys.path.insert(0, V1)

# (item, text, what we read, expected v2 value)
NUMBERS = [
    ("2  NBE glued currency",        "تم خصم 195.15EGP من حسابكم",      195.15),
    ("2  VF glued currency",         "received EGP15,608.48 from",       15608.48),
    ("2  Banque Misr glued",         "تم ايداع 11260EGP بحسابك",         11260.0),
    ("2  Banque Misr مبلغEGP",       "مبلغEGP 9800 تم تحويله",           9800.0),
    ("2  CIB Apple Pay balance",     "Available balance EGP209.69",      209.69),
    ("3  CIB refund leading dot",    "refund of EUR .93 processed",      0.93),
    ("-  plain, must still work",    "تم خصم 1,028.31 جنيه",             1028.31),
]

DATES = [
    ("1  VF-Cash YY-MM-DD",          "01:56 26-10-14",            "2026-10-14"),
    ("1  HSBC DDMMMYY",              "From HSBC: 31AUG26 charge",  "2026-08-31"),
    ("1  Banque Misr DD-MMM-YYYY",   "بتاريخ 30-AUG-2026 تم",      "2026-08-30"),
    ("1  VF-Cash MMM D, YYYY",       "Feb 13, 2026 5:25:00 AM",    "2026-02-13"),
    ("1  NBE branch MM/DD/YYYY",     "deposit on 08/20/2026",      "2026-08-20"),
    ("-  plain DD/MM/YY",            "يوم 10/08/26 الساعة 15:49",  "2026-08-10"),
    ("-  ISO",                       "date 2026-11-20 ok",         "2026-11-20"),
    ("-  no year -> null",           "يوم 04-17 الساعة 12:00",     None),
]

CURRENCIES = [
    ("glued right", "تم خصم 195.15EGP من", 195.15, "EGP"),
    ("glued left",  "Available balance EGP209.69", 209.69, "EGP"),
    ("spaced",      "تم خصم 250.00 جنيه من", 250.0, "EGP"),
    ("leading dot", "refund of EUR .93", 0.93, "EUR"),
]


def v1_number(text):
    try:
        from sms_model import candidates, normalize
        c = candidates(normalize(text))
        return [x[3] for x in c]
    except Exception as e:
        return f"<{type(e).__name__}>"


def v1_date(text):
    try:
        from sms_model import find_dates, normalize
        got = find_dates(normalize(text))
        return got[0][2].isoformat() if got else None
    except Exception as e:
        return f"<{type(e).__name__}>"


def main():
    fails = []

    print("=" * 78)
    print("NUMBERS  (item 2: currency glued to the number, item 3: leading dot)")
    print("=" * 78)
    for item, text, want in NUMBERS:
        n = spans.normalize(text)
        got = [v for _, _, _, v in spans.number_spans(n, spans.masked_regions(n))]
        ok = want in got
        if not ok:
            fails.append((item, want, got))
        print(f"  [{'ok' if ok else 'FAIL':4s}] {item:30s} want {want:<12} "
              f"v2 {got}  |  v1 {v1_number(text)}")

    print()
    print("=" * 78)
    print("DATES  (item 1: date formats v1's rules do not know)")
    print("=" * 78)
    for item, text, want in DATES:
        n = spans.normalize(text)
        found = [d for _, _, d in spans.date_spans(n) if d is not None]
        got = found[0].isoformat() if found else None
        ok = got == want
        if not ok:
            fails.append((item, want, got))
        print(f"  [{'ok' if ok else 'FAIL':4s}] {item:30s} want {str(want):<12} "
              f"v2 {str(got):<12} |  v1 {v1_date(text)}")

    print()
    print("=" * 78)
    print("CURRENCY next to the amount")
    print("=" * 78)
    for item, text, amount, want in CURRENCIES:
        n = spans.normalize(text)
        cands = spans.number_spans(n, spans.masked_regions(n))
        span = next(((s, e) for s, e, _, v in cands if abs(v - amount) < 1e-6), None)
        got = spans.currency_for(n, span)
        ok = got == want
        if not ok:
            fails.append((item, want, got))
        print(f"  [{'ok' if ok else 'FAIL':4s}] {item:30s} want {want:<6} v2 {got}")

    print()
    if fails:
        print(f"{len(fails)} FAILED")
        for item, want, got in fails:
            print(f"   {item}: wanted {want}, got {got}")
        return 1
    print(f"all {len(NUMBERS) + len(DATES) + len(CURRENCIES)} span tests passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
