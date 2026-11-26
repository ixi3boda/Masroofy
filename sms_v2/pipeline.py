"""Gate + extractor -> a record in v1's exact schema.

The decode rules that are NOT learned are kept here, deliberately few:
  * a transaction must carry an amount (v1 does the same, so the comparison is fair)
  * "no fees" stated in words -> fee = 0.0  (31 records in the corpus say it in words;
    there is no number to tag, see dataset.py coverage)
  * a tagged DATE/TIME span is turned into a value by spans.parse_*, which is where
    31AUG26 and 26-10-14 get read correctly
  * currency falls back to the nearest currency token when the CURRENCY tag is absent
"""
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import spans
from dataset import decode_bio
from marbert import MAX_LEN
from schema import CHANNELS, TYPES, empty_record

NO_FEE = re.compile(r"بدون (?:مصاريف|رسوم)|مفيش رسوم|no fees?|free of charge|"
                    r"fees?:?\s*0(?:\.0+)?\b", re.I)


def _number_in(text):
    """Read a value out of a tagged span, tolerating a glued currency (EGP450.00)."""
    got = spans.number_spans(spans.normalize(text))
    return got[0][3] if got else None


def _digits(text):
    m = re.findall(r"\d+", text)
    return m[-1] if m else None


def _last4(text):
    """Account/card suffix out of a tagged span.

    Tokenizers keep a long account number whole ("رقم 7490606815708931"), and the
    corpus convention is the last four digits — so trim. Shorter runs are left
    alone: HSBC writes three ("074-234***-001" -> "001").
    """
    d = _digits(text)
    if d is None:
        return None
    return d[-4:] if len(d) > 4 else d


# Arabic punctuation (، ؛ ؟ ٪ ...) lives inside the same U+0600-U+06FF block as the
# letters, so a letters-only character class swallows it and the merchant span comes
# back as "مروان رشدي،". Strip it at both ends.
#
# NOT stripped: * and #. NBE masks counterparty names and gold keeps the mask
# verbatim ("نورهان ع********"), so an asterisk is part of the value.
_EDGE_PUNCT = re.compile(r"^[\s،؛؟٪-٭.,;:!?'\"/\\|]+"
                         r"|[\s،؛؟٪-٭.,;:!?'\"/\\|]+$")
_PAIRS = {")": "(", "]": "[", "}": "{"}


def _trim(text):
    """Strip edge punctuation, keeping a bracket that closes one inside the span.

    "NOON (INSTANT)" is a real merchant name in this corpus, so the final ")"
    survives; a stray ")" with no opener does not.
    """
    out = _EDGE_PUNCT.sub("", text)
    while out and out[-1] in _PAIRS and out.count(_PAIRS[out[-1]]) < out.count(out[-1]):
        out = _EDGE_PUNCT.sub("", out[:-1])
    while out and out[0] in _PAIRS.values():
        closer = {v: k for k, v in _PAIRS.items()}[out[0]]
        if out.count(closer) >= out.count(out[0]):
            break
        out = _EDGE_PUNCT.sub("", out[1:])
    return out


class Pipeline:
    """Holds a gate and an extractor and turns SMS text into records."""

    def __init__(self, gate, extractor=None, tokenizer=None, meta=None, device=None,
                 max_len=MAX_LEN, batch_size=32):
        self.gate = gate
        self.gate_tok = None          # set by load() for a MARBERT gate
        self.extractor = extractor
        self.tok = tokenizer
        self.meta = meta or {}
        self.device = device
        self.max_len = max_len
        self.batch_size = batch_size
        labels = (self.meta.get("token_labels") or [])
        self.id2label = {i: l for i, l in enumerate(labels)}
        self.types = self.meta.get("types") or TYPES
        self.channels = self.meta.get("channels") or CHANNELS

    # ---------------------------------------------------------------- stage 1
    def gate_predict(self, texts):
        if hasattr(self.gate, "predict") and getattr(self.gate, "name", "") == "linear":
            return self.gate.predict(texts)
        import torch
        out = []
        for i in range(0, len(texts), self.batch_size):
            chunk = [spans.bmp(t) for t in texts[i:i + self.batch_size]]
            enc = self.gate_tok(chunk, truncation=True, max_length=self.max_len,
                                padding=True, return_tensors="pt")
            enc = {k: v.to(self.device) for k, v in enc.items()}
            with torch.no_grad():
                logits = self.gate(**enc).logits
            prob = torch.softmax(logits, dim=-1).cpu()
            for p in prob:
                out.append((bool(int(p.argmax()) == 1), round(float(p.max()), 3)))
        return out

    # ---------------------------------------------------------------- stage 2
    def extract(self, texts):
        """-> list of ({TAG: span_text}, {TAG: (start, end)}, type, channel) per text."""
        import torch
        results = []
        for i in range(0, len(texts), self.batch_size):
            chunk = [spans.bmp(t) for t in texts[i:i + self.batch_size]]
            enc = self.tok(chunk, truncation=True, max_length=self.max_len, padding=True,
                           return_offsets_mapping=True, return_tensors="pt")
            offsets = enc.pop("offset_mapping")
            enc = {k: v.to(self.device) for k, v in enc.items()}
            with torch.no_grad():
                tok_logits, type_logits, chan_logits = self.extractor(
                    input_ids=enc["input_ids"], attention_mask=enc["attention_mask"])
            tok_ids = tok_logits.argmax(-1).cpu()
            types = type_logits.argmax(-1).cpu()
            chans = chan_logits.argmax(-1).cpu()
            for j, text in enumerate(chunk):
                n = int(enc["attention_mask"][j].sum())
                offs = [tuple(map(int, o)) for o in offsets[j][:n]]
                found = decode_bio(offs, tok_ids[j][:n].tolist(), text, self.id2label)
                results.append(({t: text[s:e] for t, (s, e) in found.items()},
                                found,
                                self.types[int(types[j])],
                                self.channels[int(chans[j])]))
        return results

    # ---------------------------------------------------------------- both
    def predict_many(self, texts):
        gate = self.gate_predict(texts)
        out = [None] * len(texts)
        todo = [i for i, (is_tx, _) in enumerate(gate) if is_tx]
        for i, (is_tx, conf) in enumerate(gate):
            if not is_tx:
                rec = empty_record()
                rec["_confidence"] = conf
                rec["_reason"] = "gate: not a transaction"
                out[i] = rec
        if todo and self.extractor is not None:
            got = self.extract([texts[i] for i in todo])
            for i, g in zip(todo, got):
                out[i] = self._assemble(texts[i], g, gate[i][1])
        elif todo:
            for i in todo:                   # gate only, no extractor loaded
                rec = empty_record()
                rec["is_transaction"] = True
                rec["_confidence"] = gate[i][1]
                rec["_reason"] = "no extractor loaded"
                out[i] = rec
        return out

    def predict(self, sms):
        return self.predict_many([sms])[0]

    def _assemble(self, raw, got, conf):
        span_text, span_pos, typ, chan = got
        text = spans.bmp(raw)
        n = spans.normalize(text)
        rec = empty_record()
        rec["_confidence"] = conf

        # Numeric fields are read from the NORMALIZED text: normalize() is 1:1 per
        # character, so the same offsets hold, and ٧٣١٦ arrives as 7316 — which is
        # what the gold data stores.
        num_text = {t: n[s:e] for t, (s, e) in span_pos.items()}

        amount = _number_in(num_text["AMOUNT"]) if "AMOUNT" in num_text else None
        if amount is None:
            # v1 rejects a transaction with no amount; mirror that exactly.
            rec["is_transaction"] = False
            rec["_reason"] = "no amount found"
            return rec

        rec["is_transaction"] = True
        rec["type"] = typ
        rec["channel"] = chan
        rec["amount"] = amount

        if "FEE" in num_text:
            rec["fee"] = _number_in(num_text["FEE"])
        elif NO_FEE.search(n):
            rec["fee"] = 0.0
        if "BALANCE" in num_text:
            rec["balance_after"] = _number_in(num_text["BALANCE"])
        if "LAST4" in num_text:
            rec["account_last4"] = _last4(num_text["LAST4"])
        if "MERCHANT" in span_text:
            # from the RAW text: a merchant may legitimately be a phone number
            # written in Arabic-Indic digits, and gold keeps it as written.
            merchant = _trim(span_text["MERCHANT"])
            rec["merchant"] = merchant or None

        if "CURRENCY" in span_text:
            code = spans.CURRENCY_CODE.get(span_text["CURRENCY"].strip().lower())
            rec["currency"] = code or spans.currency_for(n, span_pos.get("AMOUNT"))
        else:
            rec["currency"] = spans.currency_for(n, span_pos.get("AMOUNT"))

        date = spans.parse_date_text(num_text["DATE"]) if "DATE" in num_text else None
        time = spans.parse_time_text(num_text["TIME"]) if "TIME" in num_text else None
        rec["datetime"] = spans.iso(date, time)
        return rec


# ------------------------------------------------------------------ loading
def load(run_dir, device="auto"):
    """Load whatever is in a run directory: gate (linear or MARBERT) + extractor."""
    from marbert import load_extractor, load_gate, load_meta, pick_device
    gate_dir = os.path.join(run_dir, "gate")
    ext_dir = os.path.join(run_dir, "extractor")
    if not os.path.isdir(gate_dir):
        raise SystemExit(f"no gate in {run_dir}\ntrain one:  python train.py --split "
                         f"{os.path.basename(run_dir)} --stage gate")

    meta = load_meta(gate_dir)
    dev = None
    if meta.get("backend") == "linear":
        from linear_gate import LinearGate
        gate, gate_tok = LinearGate.load(gate_dir), None
    else:
        dev = pick_device(device)
        gate, gate_tok, _ = load_gate(gate_dir, dev)

    extractor = tok = ext_meta = None
    if os.path.isdir(ext_dir):
        dev = dev or pick_device(device)
        extractor, tok, ext_meta = load_extractor(ext_dir, dev)

    pipe = Pipeline(gate, extractor, tok, ext_meta, dev)
    pipe.gate_tok = gate_tok
    return pipe
