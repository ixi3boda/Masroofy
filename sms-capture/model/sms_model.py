#!/usr/bin/env python3
"""SMS transaction detector & field extractor for Egyptian bank / wallet SMS (Arabic, English, mixed).

Pipeline (all scikit-learn, CPU, < 1 MB model):
  0. normalize      Arabic-Indic digits/separators -> ASCII, 1:1 per character (offsets preserved)
  1. type model     char + word TF-IDF -> logistic regression -> {none, debit, credit, transfer_out,
                    transfer_in, atm_withdrawal, bill_payment, other}; "none" = not a transaction
  2. channel model  same features -> {card, instapay, wallet, bank_transfer, atm, other, unknown}
  3. number roles   every number in the SMS is a candidate; a logistic regression on its context
                    labels it amount / fee / balance / last4 / other
  4. merchant tagger per-token B/I/O logistic regression with a +-2 token window; best span decoded
  5. rules          dates/times (finite set of formats) and currency (lexicon next to the amount)

Usage:
  python3 sms_model.py train  data.jsonl  model.joblib
  python3 sms_model.py predict model.joblib "SMS text"            # one message
  python3 sms_model.py predict model.joblib --jsonl in.jsonl > out.jsonl
"""
import json, re, sys, datetime as dt
import numpy as np
from scipy.sparse import hstack
from sklearn.feature_extraction import DictVectorizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
import joblib

# ------------------------------------------------------------------ normalization
_NORM = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹٬٫", "0123456789" "0123456789" ",.")
def bmp(s: str) -> str:
    """Replace characters outside the Basic Multilingual Plane (emoji) with U+FFFD.
    Makes character offsets identical in Python (code points) and Java/Kotlin/JS (UTF-16 units)."""
    return "".join(c if ord(c) <= 0xFFFF else "\uFFFD" for c in s)

def normalize(s: str) -> str:
    return bmp(s).translate(_NORM)     # same length as input -> spans map back to the original text

# ------------------------------------------------------------------ rules: dates, times, currency
MON = {m: i + 1 for i, m in enumerate("jan feb mar apr may jun jul aug sep oct nov dec".split())}
MON_AR = {m: i + 1 for i, m in enumerate(["يناير","فبراير","مارس","أبريل","مايو","يونيو","يوليو",
                                          "أغسطس","سبتمبر","أكتوبر","نوفمبر","ديسمبر"])}
MON_AR.update({"ابريل": 4, "اكتوبر": 10, "اغسطس": 8})
RE_DMY = re.compile(r"(?<![\d.,/-])(\d{1,2})([/.\-])(\d{1,2})\2(\d{4}|\d{2})(?![\d/])")
RE_DMON = re.compile(r"(?<!\d)(\d{1,2})\s+(" + "|".join(list(MON_AR)) + r"|[A-Za-z]{3,9}),?\s+(\d{4})(?!\d)")
RE_TIME = re.compile(r"(?<![\d:.])([01]?\d|2[0-3]):([0-5]\d)(?::[0-5]\d)?(?:\s*(AM|PM|am|pm|ص|م)(?![\w]))?(?![\d])")
CURRENCY = [("EGP", "EGP"), ("LE", "EGP"), ("L.E", "EGP"), ("جنيه", "EGP"), ("جنية", "EGP"), ("ج.م", "EGP"),
            ("جم", "EGP"), ("USD", "USD"), ("EUR", "EUR"), ("GBP", "GBP"), ("SAR", "SAR"), ("AED", "AED")]
NO_FEE = re.compile(r"بدون (?:مصاريف|رسوم)|مفيش رسوم|no fees?|free of charge|fees?:?\s*0(?:\.0+)?\b", re.I)

def find_dates(n):
    """Return list of (start, end, date) in normalized text."""
    out = []
    for m in RE_DMY.finditer(n):
        d, mo, y = int(m.group(1)), int(m.group(3)), int(m.group(4))
        if y < 100: y += 2000
        try: out.append((m.start(), m.end(), dt.date(y, mo, d)))
        except ValueError: pass
    for m in RE_DMON.finditer(n):
        name = m.group(2); mo = MON_AR.get(name) or MON.get(name[:3].lower())
        if mo:
            try: out.append((m.start(), m.end(), dt.date(int(m.group(3)), mo, int(m.group(1)))))
            except ValueError: pass
    return sorted(out)

def find_times(n):
    out = []
    for m in RE_TIME.finditer(n):
        h, mi, ap = int(m.group(1)), int(m.group(2)), m.group(3)
        if ap:
            pm = ap.lower() in ("pm", "م")
            if h == 12: h = 0
            if pm: h += 12
        if h > 23: continue
        out.append((m.start(), m.end(), dt.time(h, mi)))
    return out

def currency_near(n, s, e):
    """Currency token touching the amount (within 3 chars on either side)."""
    right, left = n[e:e + 8].lstrip(), n[max(0, s - 8):s].rstrip()
    for tok, code in CURRENCY:
        if right.startswith(tok) and not re.match(r"[A-Za-z]", right[len(tok):len(tok) + 1] or " ") \
                and len(n[e:e + 8]) - len(right) <= 3:
            return code
        if left.endswith(tok) and len(n[max(0, s - 8):s]) - len(left) <= 3:
            return code
    return None

# ------------------------------------------------------------------ number candidates
RE_NUM = re.compile(r"(?<![A-Za-z\d.,])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![A-Za-z\d])")
RE_XX = re.compile(r"(?<![A-Za-z])[xX]{1,4}(\d{3,4})(?!\d)")
def candidates(n):
    masked = [(s, e) for s, e, _ in find_dates(n) + find_times(n)]
    out = [(m.start(1), m.end(1), m.group(1), float(m.group(1))) for m in RE_XX.finditer(n)]
    for m in RE_NUM.finditer(n):
        s, e = m.span(1)
        if any(a <= s < b for a, b in masked): continue
        txt = m.group(1)
        try: val = float(txt.replace(",", ""))
        except ValueError: continue
        out.append((s, e, txt, val))
    return sorted(out)

TOK = re.compile(r"[A-Za-z؀-ۿ]+|\d+|[^\s\w]", re.UNICODE)
def ctx_tokens(n, s, e):
    left = TOK.findall(n[max(0, s - 40):s])[-4:]
    right = TOK.findall(n[e:e + 30])[:3]
    return [t.lower() for t in left], [t.lower() for t in right]

def num_feats(n, cands, k):
    s, e, txt, val = cands[k]
    L, Rt = ctx_tokens(n, s, e)
    f = {"bias": 1, "digits=%d" % min(len(txt.replace(",", "").split(".")[0]), 7): 1,
         "has_dec": "." in txt, "has_comma": "," in txt, "dec2": bool(re.search(r"\.\d\d$", txt)),
         "len4_int": len(txt) == 4 and txt.isdigit(), "lead0": txt.startswith("0") and len(txt) > 1,
         "rank=%d" % min(k, 5): 1, "rev_rank=%d" % min(len(cands) - 1 - k, 5): 1,
         "is_max": val == max(c[3] for c in cands), "is_min": val == min(c[3] for c in cands),
         "prev_char=" + (n[s - 1] if s > 0 else "^"): 1, "next_char=" + (n[e] if e < len(n) else "$"): 1,
         "cur_near": currency_near(n, s, e) is not None,
         # any masking style (****1234, *1234, #1234, xx1234, ending 1234) maps to one generic feature
         "masked": bool(MASKED_RE.search(n[max(0, s - 22):s]))}
    lc, ld = nearest_cue(n[max(0, s - 35):s], "L"); rc, rd = nearest_cue(n[e:e + 12], "R")
    if lc: f["Lcue=" + lc] = 1; f["Lcue=%s|d%d" % (lc, min(ld // 8, 3))] = 1
    if rc: f["Rcue=" + rc] = 1
    for i, t in enumerate(reversed(L)): f[f"L{i}={t}"] = 1
    for i, t in enumerate(Rt): f[f"R{i}={t}"] = 1
    if len(L) >= 2: f[f"L10={L[-2]}|{L[-1]}"] = 1
    for t in L: f["Lbag=" + t] = 1
    for t in Rt: f["Rbag=" + t] = 1
    return f

CUES = {
 "bal": r"رصيد|رصيك|الرصبد|balance|balnce|\bbal\b|avl|الباقي|المتاح|المتبقي",
 "fee": r"رسوم|رسزم|مصاريف|عمولة|\bfees?\b|charges?\b|service fee",
 "amt": r"مبلغ|مبلع|بقيمة|amount|purchase|charged for|debited|credited|withdrawal|withdrawn|sent|received|paid|"
        r"refund|deposit|تحويل|تحوبل|خصم|إيداع|ايداع|سحب|سحبت|استلام|وصلك|دفع|دفعت|بعت|استلمت|اتحولوا|رد|استرداد|شحن",
 "ref": r"رقم العملي|المرجع|\bref|reference|txn|transaction id|رقم الحركة",
 "card": r"\*|#|\bxx|ending|المنتهي|card|كارت|بطاق|a/c|حساب",
 "limit": r"limit|الحد|minimum|القسط|installment|monthly|قسط",
 "pct": r"%|٪",
}
CUE_RE = {k: re.compile(v, re.I) for k, v in CUES.items()}
def nearest_cue(window, side):
    best, bd = None, 10 ** 6
    for k, rx in CUE_RE.items():
        for m in rx.finditer(window):
            d = len(window) - m.end() if side == "L" else m.start()
            if d < bd: best, bd = k, d
    return best, bd

MASKED_RE = re.compile(r"(?:[*#]|\b[xX]{1,4}|ending(?: with)?|المنتهية بـ?|المنتهي بـ?)\s*$")
ROLES = ["amount", "fee", "balance", "last4", "other"]
def num_labels(n, cands, exp):
    labs, used = [], set()
    for s, e, txt, val in cands:
        lab = "other"
        if exp.get("is_transaction"):
            if exp.get("amount") is not None and abs(val - exp["amount"]) < 1e-6 and "amount" not in used: lab = "amount"
            elif exp.get("fee") and abs(val - exp["fee"]) < 1e-6 and "fee" not in used: lab = "fee"
            elif exp.get("balance_after") is not None and abs(val - exp["balance_after"]) < 1e-6 and "balance" not in used: lab = "balance"
            elif exp.get("account_last4") and txt == exp["account_last4"] and "last4" not in used: lab = "last4"
        used.add(lab); labs.append(lab)
    return labs

# ------------------------------------------------------------------ merchant tagger
WTOK = re.compile(r"[A-Za-z0-9؀-ۿ]+(?:[.'&][A-Za-z0-9؀-ۿ]+)*|[^\s]", re.UNICODE)
def wtokens(text):
    return [(m.start(), m.end(), m.group()) for m in WTOK.finditer(text)]

def shape(w):
    if re.fullmatch(r"\d+", w): return "D"
    if re.fullmatch(r"[؀-ۿ]+", w): return "AR"
    if w.isupper() and w.isalpha(): return "UP"
    if w[:1].isupper(): return "Title"
    if w.isalpha(): return "low"
    return "P:" + w if len(w) == 1 else "mix"

TCLASS = [("PREP", r"لـ|ل|إلى|الى|من|لدى|لدي|في|عند|at|to|from|in|for"),
          ("DATEKW", r"بتاريخ|يوم|on|date|الساعة|الساعه|بالـ|via"),
          ("SYS", r"محفظ\w*|حساب\w*|بطاق\w*|كارت|الكارت|wallet|account|card|atm|ماكينة|instapay|انستاباي|ipn|qr"),
          ("CUR", r"egp|le|جنيه|جنية|ج|م|usd|eur|gbp|sar|aed"),
          ("AMTKW", r"مبلغ|بمبلغ|بقيمة|amount|purchase|of"),
          ("BALKW", r"رصيد\w*|رصيك|balance|bal|avl|available"),
          ("FEEKW", r"رسوم|مصاريف|fee|fees")]
TCLASS_RE = [(k, re.compile(r"(?:%s)" % v, re.I)) for k, v in TCLASS]
def tclass(w):
    if re.fullmatch(r"\d+", w): return "NUM"
    for k, rx in TCLASS_RE:
        if rx.fullmatch(w): return k
    if len(w) == 1 and not w.isalnum(): return "PUNCT"
    return "WORD"

def tok_feats(toks, i):
    def w(j):
        return toks[j][2].lower() if 0 <= j < len(toks) else ("<s>" if j < 0 else "</s>")
    def sh(j):
        return shape(toks[j][2]) if 0 <= j < len(toks) else "PAD"
    f = {"bias": 1, "w=" + w(i): 1, "sh=" + sh(i): 1, "w-1=" + w(i - 1): 1, "w-2=" + w(i - 2): 1,
         "w+1=" + w(i + 1): 1, "w+2=" + w(i + 2): 1, "sh-1=" + sh(i - 1): 1, "sh+1=" + sh(i + 1): 1,
         "w-1|w=" + w(i - 1) + "|" + w(i): 1, "sh-1|sh|sh+1=" + "|".join([sh(i - 1), sh(i), sh(i + 1)]): 1,
         "pos=" + str(min(i, 12) // 3): 1}
    def tc(j): return tclass(toks[j][2]) if 0 <= j < len(toks) else "PAD"
    for d in (-2, -1, 0, 1, 2): f[f"c{d}=" + tc(i + d)] = 1
    f["c-1|c0|c+1=" + "|".join([tc(i - 1), tc(i), tc(i + 1)])] = 1
    f["c-2|c-1=" + tc(i - 2) + "|" + tc(i - 1)] = 1
    f["c0|c+1|c+2=" + "|".join([tc(i), tc(i + 1), tc(i + 2)])] = 1
    for k in range(1, 6):   # nearest left anchor word (e.g. "لدى", "at", "to", "from", "إلى")
        if i - k >= 0 and toks[i - k][2].lower() in ANCHORS:
            f["anchor=" + toks[i - k][2].lower()] = 1; f["anchor_dist=%d" % k] = 1; break
    return f

ANCHORS = {"at", "to", "from", "لدى", "لدي", "إلى", "الى", "من", "لـ", "ل", "في", "فاتورة", "عداد", "salary",
           "for", "-", "paid", "transfer", "in", "عند"}

def bio_labels(toks, text, merchant):
    labs = ["O"] * len(toks)
    if not merchant: return labs
    s = text.find(merchant)
    if s < 0: return labs
    e = s + len(merchant); first = True
    for i, (a, b, _) in enumerate(toks):
        if a >= s and b <= e:
            labs[i] = "B" if first else "I"; first = False
    return labs

# ------------------------------------------------------------------ the model
# Domain cue lexicon: generic words that signal direction / kind / channel in ANY Egyptian bank SMS.
# They let the classifiers generalise to wordings and senders not seen in training.
LEX = {
 "out": r"خصم|سحب|شراء|دفع|دفعت|سداد|إرسال|ارسال|بعت|اتحول|تم تحويل|استخدام|debited|debit|charged|purchase|spent|used|paid|sent|withdraw|transferred to|payment of|you paid|deducted",
 "in": r"إيداع|ايداع|استلام|استلمت|وصلك|إضافة|اضافة|رد |استرداد|استرجاع|عكس|credited|received|refund|reversal|reversed|deposit|returned",
 "refund": r"رد |استرداد|استرجاع|عكس|إلغاء|refund|reversal|reversed|returned|cancel",
 "salary": r"راتب|مرتب|salary|payroll|حوالة واردة|incoming transfer",
 "atm": r"\bATM\b|صراف|ماكينة|سحب نقدي|cash withdrawal|withdrawn|سحبت",
 "bill": r"فاتور|عداد|bill|biller|subscriber",
 "card": r"بطاق|كارت|card|POS|visa|mastercard|meeza|ميزة|\*{2,}\d|with#",
 "instapay": r"انستا ?باي|instapay|IPN|تحويل لحظي|@instapay|instant transfer",
 "wallet": r"محفظ|wallet|QR|كاش|top-?up|شحن",
 "bank": r"حساب|A/C|account|فرع|branch",
 "fail": r"رفض|تعذر|فشل|مكملتش|اترفض|declined|failed|could not|not approved|unsuccessful|لم يتم الخصم|no amount",
 "otp": r"OTP|رمز التحقق|كود (?:ال)?(?:تحقق|تأكيد|تفعيل|دفع|دخول)|كود التأكيد|verification code|login code|payment code|كلمة السر|password|one-time|لا تشارك|متديهوش|don't share|never share",
 "promo": r"عرض|قرض|اشحن|ادفع أي|حوّل لأي|فعّل|قسّط|كاش باك|cashback|offer|loan|pre-approved|eligible|installments for|reward|اشترك|مبروك|congratulations|won",
 "due": r"مستحق|استحقاق|تذكير|due|reminder|minimum",
 "balance_only": r"^(?!.*(خصم|إيداع|تحويل|debited|credited|purchase)).*(رصيد|balance|limit)",
 "link": r"\.example|https?://|www\.|\b[a-z0-9-]+\.(?:com|net|eg|xyz|info)\b",
 "security": r"جهاز جديد|new device|تغيير|changed|blocked|suspicious|login|تسجيل دخول",
}
LEX_RE = {k: re.compile(v, re.I) for k, v in LEX.items()}
def lex_feats(n):
    f = {}
    for k, rx in LEX_RE.items():
        if rx.search(n): f["lex=" + k] = 1.0
    if not candidates(n): f["no_number"] = 1.0
    return f

TYPES = ["none", "debit", "credit", "transfer_out", "transfer_in", "atm_withdrawal", "bill_payment", "other"]

class SmsTxnModel:
    def __init__(self, C_text=8.0, C_num=4.0, C_tok=4.0, lex_w=1.0, thr=0.35):
        self.C_text, self.C_num, self.C_tok, self.lex_w, self.thr = C_text, C_num, C_tok, lex_w, thr

    # -- text features shared by the type and channel classifiers
    def _fit_text(self, texts):
        self.v_char = TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 5), min_df=2, sublinear_tf=True)
        self.v_word = TfidfVectorizer(analyzer="word", token_pattern=r"[A-Za-z؀-ۿ]+",
                                      ngram_range=(1, 2), min_df=2, sublinear_tf=True, lowercase=True)
        self.v_lex = DictVectorizer()
        L = self.v_lex.fit_transform([lex_feats(t) for t in texts]) * self.lex_w
        return hstack([self.v_char.fit_transform(texts), self.v_word.fit_transform(texts), L]).tocsr()
    def _text(self, texts):
        L = self.v_lex.transform([lex_feats(t) for t in texts]) * self.lex_w
        return hstack([self.v_char.transform(texts), self.v_word.transform(texts), L]).tocsr()

    def fit(self, records):
        texts = [normalize(r["sms"]) for r in records]
        X = self._fit_text(texts)
        y_type = [r["expected"]["type"] if r["expected"]["is_transaction"] else "none" for r in records]
        self.type_clf = LogisticRegression(C=self.C_text, max_iter=3000, class_weight="balanced").fit(X, y_type)
        tx = [i for i, t in enumerate(y_type) if t != "none"]
        self.chan_clf = LogisticRegression(C=self.C_text, max_iter=3000).fit(
            X[tx], [records[i]["expected"]["channel"] for i in tx])
        # number roles
        F, Y = [], []
        for r, n in zip(records, texts):
            c = candidates(n)
            labs = num_labels(n, c, r["expected"])
            for k in range(len(c)):
                F.append(num_feats(n, c, k)); Y.append(labs[k])
        self.v_num = DictVectorizer()
        self.num_clf = LogisticRegression(C=self.C_num, max_iter=3000).fit(self.v_num.fit_transform(F), Y)
        # merchant tagger (transactions only)
        F, Y = [], []
        for i in tx:
            text = bmp(records[i]["sms"]); toks = wtokens(text)
            labs = bio_labels(toks, text, records[i]["expected"]["merchant"])
            for j in range(len(toks)):
                F.append(tok_feats(toks, j)); Y.append(labs[j])
        self.v_tok = DictVectorizer()
        self.tok_clf = LogisticRegression(C=self.C_tok, max_iter=3000).fit(self.v_tok.fit_transform(F), Y)
        return self

    def predict(self, sms: str) -> dict:
        sms = bmp(sms); n = normalize(sms); X = self._text([n])
        p = self.type_clf.predict_proba(X)[0]; classes = list(self.type_clf.classes_)
        typ = classes[int(np.argmax(p))]
        out = {"is_transaction": typ != "none", "type": None, "amount": None, "currency": None, "fee": None,
               "balance_after": None, "merchant": None, "channel": None, "datetime": None, "account_last4": None,
               "_confidence": round(float(np.max(p)), 3)}
        if typ == "none": return out
        cands = [c for c in candidates(n) if c[3] > 0]
        if not cands:          # a transaction must carry an amount; otherwise reject
            out["is_transaction"] = False; out["_reason"] = "no amount found"; return out
        out["type"] = str(typ)
        out["channel"] = str(self.chan_clf.predict(X)[0])
        P = self.num_clf.predict_proba(self.v_num.transform([num_feats(n, cands, k) for k in range(len(cands))]))
        ci = {c: i for i, c in enumerate(self.num_clf.classes_)}
        taken = set()
        def pick(role, thr):
            if role not in ci: return None
            order = np.argsort(-P[:, ci[role]])
            for k in order:
                if k not in taken and P[k, ci[role]] >= thr:
                    taken.add(k); return k
            return None
        ka = pick("amount", 0.0)
        s, e, txt, val = cands[ka]
        out["amount"] = val; out["currency"] = currency_near(n, s, e)
        kf = pick("fee", self.thr); kb = pick("balance", self.thr); kl = pick("last4", self.thr)
        if kf is not None: out["fee"] = cands[kf][3]
        elif NO_FEE.search(n): out["fee"] = 0.0
        if kb is not None: out["balance_after"] = cands[kb][3]
        if kl is not None: out["account_last4"] = cands[kl][2]
        # datetime: first date in the message, plus a time if present
        ds, ts = find_dates(n), find_times(n)
        if ds:
            d = ds[0][2]
            out["datetime"] = (dt.datetime.combine(d, ts[0][2]).strftime("%Y-%m-%dT%H:%M:00") if ts
                               else d.isoformat())
        # merchant span
        toks = wtokens(sms)
        if toks:
            PT = self.tok_clf.predict_proba(self.v_tok.transform([tok_feats(toks, j) for j in range(len(toks))]))
            ti = {c: i for i, c in enumerate(self.tok_clf.classes_)}
            b = PT[:, ti["B"]]; j = int(np.argmax(b))
            if b[j] >= 0.35:
                k = j
                while k + 1 < len(toks) and PT[k + 1, ti["I"]] >= 0.3 and PT[k + 1, ti["I"]] >= PT[k + 1, ti["B"]]: k += 1
                out["merchant"] = sms[toks[j][0]:toks[k][1]]
        return out

    def save(self, path): joblib.dump(self, path, compress=3)
    @staticmethod
    def load(path): return joblib.load(path)

# ------------------------------------------------------------------ CLI
def _read(path): return [json.loads(l) for l in open(path, encoding="utf-8") if l.strip()]

if __name__ == "__main__":
    from sms_model import SmsTxnModel   # pickle the class as sms_model.SmsTxnModel, loadable from any script
    if len(sys.argv) >= 4 and sys.argv[1] == "train":
        m = SmsTxnModel().fit(_read(sys.argv[2])); m.save(sys.argv[3]); print("saved", sys.argv[3])
    elif len(sys.argv) >= 4 and sys.argv[1] == "predict":
        m = SmsTxnModel.load(sys.argv[2])
        if sys.argv[3] == "--jsonl":
            for r in _read(sys.argv[4]):
                print(json.dumps({"id": r.get("id"), "sms": r["sms"], "predicted": m.predict(r["sms"])}, ensure_ascii=False))
        else:
            print(json.dumps(m.predict(sys.argv[3]), ensure_ascii=False, indent=2))
    else:
        print(__doc__)
