#!/usr/bin/env python3
"""Turn SMS exported from your own phone into anonymized, pre-labelled training data.

Supported input (detected by extension):
  .xml    "SMS Backup & Restore" export (Android app)  <sms address=".." body=".." date=".."/>
  .json   same app's JSON, or [{"_address": .., "messages": [{"_body": .., "_date": ..}]}]
  .csv    columns: address, body[, date]
  .txt    output of: adb shell content query --uri content://sms/inbox --projection address:body:date

What it does:
  1. keeps messages from Egyptian bank / wallet / finance senders (plus any message that looks financial)
  2. anonymizes: phone numbers, account / card digits, reference numbers, InstaPay handles and people's
     names in the usual slots (المسجل بإسم / من / إلى / from / to) are replaced with consistent fakes.
     Amounts, balances, dates and merchant names are kept. ALWAYS skim the output before sharing it.
  3. pre-labels each message with your SmsTxnModel (if a model file is given) and marks it needs_review

Usage:
  python3 import_my_sms.py sms-backup.xml my_real_sms.jsonl [model.joblib] [--start-id 5001]
  -> my_real_sms.jsonl (dataset schema) + my_real_sms.manifest.csv (template_id = message shape)
"""
import csv, hashlib, json, random, re, sys
import xml.etree.ElementTree as ET

FIN_SENDERS = re.compile(
    r"VF-?Cash|Vodafone|BanK-?AlAhly|\bNBE\b|\bCIB|HSBC|Banque ?Misr|BanqueMisr|\bBM\b|QNB|AAIB|Banque ?du ?Caire|"
    r"\bBDC\b|Alex ?Bank|\bADIB|Faisal|EG ?Bank|Credit ?Agricole|\bCAE\b|AttijariWafa|Emirates ?NBD|\bSAIB|\bABK|"
    r"Orange ?(Cash|Money)|Etisalat ?Cash|e& ?cash|WE ?Pay|InstaPay|valU|Fawry|Telda|Halan|Contact|Souhoola|Sympl|"
    r"Aman|Khazna|Paymob|Forsa|MidTakseet|Premium ?Card", re.I)
LOOKS_FINANCIAL = re.compile(r"(جنيه|جم\b|ج\.م|EGP|\bLE\b).*(حساب|بطاق|محفظ|كاش|account|card|wallet|balance|رصيد)", re.I | re.S)

def read(path):
    if path.endswith(".xml"):
        for e in ET.parse(path).getroot().iter("sms"):
            yield e.get("address", ""), e.get("body", ""), e.get("date")
    elif path.endswith(".json"):
        data = json.load(open(path, encoding="utf-8"))
        for g in data:
            if "messages" in g:
                for m in g["messages"]: yield g.get("_address") or g.get("address", ""), m.get("_body") or m.get("body", ""), m.get("_date") or m.get("date")
            else: yield g.get("address") or g.get("sender", ""), g.get("body") or g.get("sms", ""), g.get("date")
    elif path.endswith(".csv"):
        for r in csv.DictReader(open(path, encoding="utf-8-sig")): yield r.get("address", ""), r.get("body", ""), r.get("date")
    else:   # adb content query output; bodies may span lines
        txt = open(path, encoding="utf-8").read()
        for m in re.finditer(r"Row: \d+ address=(.*?), body=(.*?), date=(\d+)\s*(?=Row: |\Z)", txt, re.S):
            yield m.group(1), m.group(2), m.group(3)

# ------------------------------------------------------------------ anonymization (consistent within one run)
_map, _rng = {}, random.Random(0)
def fake(kind, orig, gen):
    return _map.setdefault((kind, orig), gen())
def rdig(k): return "".join(_rng.choice("0123456789") for _ in range(k))
FAKE_AR = ["أحمد سامي", "منى عادل", "محمد فتحي", "سارة حسين", "كريم نبيل", "هبة شوقي", "عمر رشدي", "نهى مختار"]
FAKE_EN = ["AHMED SAMY", "MONA ADEL", "MOHAMED FATHY", "SARA HUSSEIN", "KARIM NABIL", "HEBA SHAWKY", "OMAR ROSHDY"]

def fake_name(n):
    def gen():
        pool = FAKE_AR if re.search(r"[؀-ۿ]", n) else FAKE_EN
        f = _rng.choice(pool)
        if "*" in n: f = " ".join([f.split()[0]] + [w[0] + "*" * (len(w) - 1) for w in f.split()[1:]])
        return f.title() if n[:1].isupper() and not n.isupper() else f
    return fake("name", n, gen)

NAME_SLOTS = [   # (regex with the name in group 1)
    r"المسجل ب[إا]سم\s+(.+?)(?=\s+على رقم|[.،\n])",
    r"(?:من|إلى|الى)\s+((?:[^\s\d]+\s){0,4}[^\s\d]+?)\s+(?=رقم مرجعي|برقم مرجعي)",
    r"\b(?:from|to)\s+([A-Za-z][A-Za-z .'-]{2,40}?)\s+(?=with reference|via InstaPay)",
]
def anonymize(t):
    t = re.sub(r"[\w.]+@instapay", lambda m: fake("handle", m.group(), lambda: f"user{rdig(3)}@instapay"), t)
    for rx in NAME_SLOTS:
        t = re.sub(rx, lambda m: m.group(0).replace(m.group(1), fake_name(m.group(1))), t)
    t = re.sub(r"(?<!\d)(?:\+?20|0020|002)?01[0125]\d{8}(?!\d)", lambda m: fake("phone", m.group(), lambda: m.group()[:-8] + rdig(8)), t)
    t = re.sub(r"(?<![\d.,])\d{8,}(?![\d.,])", lambda m: fake("long", m.group(), lambda: m.group()[:3] + rdig(len(m.group()) - 3)), t)  # refs, accounts
    t = re.sub(r"\b\d{3}-\d{3}\*{3}-\d{3}\b", lambda m: fake("acct", m.group(), lambda: f"{rdig(3)}-{rdig(3)}***-{rdig(3)}"), t)   # HSBC 074-123***-001
    t = re.sub(r"(?:\*{2,}|[xX]{2,}|#\s?\*{0,4}|بـ\s*|رقم\s?|ending(?: with)?\s?#?|\*\*\*\s|Number\s)(\d{3,4})(?!\d)",
               lambda m: m.group(0)[:-len(m.group(1))] + fake("last4", m.group(1), lambda: rdig(len(m.group(1)))), t)
    t = re.sub(r"(?<=reference )[0-9a-f]{8}\b|(?<=برقم مرجعي )[0-9a-f]{8}\b", lambda m: fake("hex", m.group(), lambda: "%08x" % _rng.getrandbits(32)), t)
    return t

def shape(t):
    return hashlib.md5(re.sub(r"[\d٠-٩]+([.,٫٬]\d+)*", "#", re.sub(r"\s+", " ", t))[:80].encode()).hexdigest()[:10]

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    start = int(sys.argv[sys.argv.index("--start-id") + 1]) if "--start-id" in sys.argv else 5001
    if "--start-id" in sys.argv: args.remove(str(start))
    src, dst = args[0], args[1]
    model = None
    if len(args) > 2:
        from sms_model import SmsTxnModel
        model = SmsTxnModel.load(args[2])
    seen, rows = set(), []
    for addr, body, date in read(src):
        if not body or not (FIN_SENDERS.search(addr or "") or FIN_SENDERS.search(body[:40]) or LOOKS_FINANCIAL.search(body)):
            continue
        a = anonymize(body)
        if a in seen: continue
        seen.add(a)
        rec = {"id": start + len(rows), "sender": addr, "sms": a, "received_at": date, "needs_review": True}
        if model:
            p = model.predict(a); p.pop("_confidence", None); p.pop("_reason", None); rec["expected"] = p
        rows.append(rec)
    with open(dst, "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open(dst.rsplit(".", 1)[0] + ".manifest.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f); w.writerow(["id", "template_id", "sender", "provenance"])
        for r in rows: w.writerow([r["id"], f"{r['sender']}:{shape(r['sms'])}", r["sender"], "real"])
    print(f"kept {len(rows)} financial messages -> {dst}  (review every 'expected' block, then drop needs_review)")
