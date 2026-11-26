"""Oracle round-trip: gold fields -> character spans -> BIO -> decode -> values.

    python test_labels.py

This trains nothing. It feeds the CORRECT token labels to the decoder and checks
what comes back out, which measures everything in v2 except the model itself:
the span finders, the BIO alignment, and pipeline._assemble's parsers.

The result is v2's extraction CEILING. A field that loses accuracy here can never
be recovered by a better encoder, so this is the number to fix first — and it is
the honest way to size up v2 before paying for a GPU.

A regex tokenizer stands in for WordPiece. It is coarser, so real MARBERT
alignment can only be equal or better at the boundaries.
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import dataset
import spans
from dataset import bio_from_spans, decode_bio
from schema import FIELDS, TOKEN_LABELS

# Word / number / punctuation, with offsets — a stand-in for a fast tokenizer.
# Two things it must get right to measure the ceiling honestly:
#   * the Arabic letter range excludes U+060C-U+061F and U+066A-U+066D, which are
#     punctuation living inside the same Unicode block (WordPiece splits those off);
#   * Arabic and Latin are separate alternatives, so a script change is a token
#     boundary. That is REAL_FORMATS.md item 7: v1's WTOK makes "فيNETFLIX.COM" one
#     token, so the merchant span can never be cut out of it. A WordPiece vocabulary
#     splits there for free, since no piece spans both scripts.
TOK = re.compile(r"[A-Za-z]+(?:[.'&][A-Za-z]+)*|[ؠ-ٰٟ-ۿ]+"
                 r"|\d+(?:[.,]\d+)*|[^\s]", re.UNICODE)
ID2LABEL = {i: l for i, l in enumerate(TOKEN_LABELS)}


def tokenize(text):
    return [(m.start(), m.end()) for m in TOK.finditer(text)]


def assemble(text, found):
    """pipeline._assemble's field logic, minus the model-predicted type/channel."""
    from pipeline import NO_FEE, _last4, _number_in, _trim
    n = spans.normalize(text)
    span_text = {t: text[s:e] for t, (s, e) in found.items()}
    num_text = {t: n[s:e] for t, (s, e) in found.items()}
    rec = {f: None for f in FIELDS}

    rec["amount"] = _number_in(num_text["AMOUNT"]) if "AMOUNT" in num_text else None
    if "FEE" in num_text:
        rec["fee"] = _number_in(num_text["FEE"])
    elif NO_FEE.search(n):
        rec["fee"] = 0.0
    if "BALANCE" in num_text:
        rec["balance_after"] = _number_in(num_text["BALANCE"])
    if "LAST4" in num_text:
        rec["account_last4"] = _last4(num_text["LAST4"])
    if "MERCHANT" in span_text:
        rec["merchant"] = _trim(span_text["MERCHANT"]) or None
    if "CURRENCY" in span_text:
        rec["currency"] = (spans.CURRENCY_CODE.get(span_text["CURRENCY"].strip().lower())
                           or spans.currency_for(n, found.get("AMOUNT")))
    else:
        rec["currency"] = spans.currency_for(n, found.get("AMOUNT"))
    date = spans.parse_date_text(num_text["DATE"]) if "DATE" in num_text else None
    time = spans.parse_time_text(num_text["TIME"]) if "TIME" in num_text else None
    rec["datetime"] = spans.iso(date, time)
    return rec


def eq(a, b):
    if isinstance(a, float) and isinstance(b, float):
        return abs(a - b) < 1e-6
    return a == b


def main():
    graded = [f for f in FIELDS if f not in ("type", "channel")]   # not span-derived
    data, man = dataset.load()
    hit = {f: 0 for f in graded}
    total = 0
    full = 0
    worst = {f: [] for f in graded}

    for r in data:
        exp = r["expected"]
        if not exp["is_transaction"]:
            continue
        total += 1
        text = spans.bmp(r["sms"])
        gold = spans.gold_spans(text, exp)
        offsets = tokenize(text)
        labels = bio_from_spans(offsets, gold)
        found = decode_bio(offsets, labels, text, ID2LABEL)
        got = assemble(text, found)

        ok_all = True
        for f in graded:
            if eq(exp[f], got[f]):
                hit[f] += 1
            else:
                ok_all = False
                if len(worst[f]) < 3:
                    worst[f].append((r["sender"], exp[f], got[f], r["sms"][:70]))
        full += ok_all

    print(f"Oracle round-trip over {total} transactions")
    print("(correct labels in -> what the v2 decoder gets out; this is the ceiling)\n")
    for f in graded:
        pct = hit[f] / total
        print(f"  {f:16s} {hit[f]:5d}/{total:<5d} {pct:7.1%} {'#' * int(pct * 28)}")
    print(f"\n  {'all span fields':16s} {full:5d}/{total:<5d} {full / total:7.1%}")

    print("\nWhere the ceiling is below 100% — these are v2's remaining rule limits,"
          "\nnot model limits, so they are the cheapest thing left to fix:\n")
    clean = True
    for f in graded:
        if hit[f] == total:
            continue
        clean = False
        print(f"  {f}  ({total - hit[f]} misses)")
        for sender, want, got, sms in worst[f]:
            print(f"    [{sender}] want {want!r} got {got!r}")
            print(f"       {sms}")
    if clean:
        print("  (none)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
