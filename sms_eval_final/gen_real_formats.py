#!/usr/bin/env python3
"""Generate SMS in the real formats sent by Egyptian banks and wallets, labelled in the
SmsTxnModel schema.

Every template copies the wording, spacing and quirks of a real message (sources in
REAL_FORMATS.md). Amounts, names, phone numbers, card digits, references and dates are
synthetic, so no real person's data is reproduced.

provenance:
  verified     wording taken from real messages (device exports or real-message fixtures)
  approximate  no real sample found; modelled on the sender's known style. Replace these
               with your own messages when you have them.

Usage: python3 gen_real_formats.py [N=1200] [seed=7]
  -> sms_real_formats.jsonl, manifest_real_formats.csv
"""
import csv, json, math, random, sys, datetime as dt

N = int(sys.argv[1]) if len(sys.argv) > 1 else 1200
R = random.Random(int(sys.argv[2]) if len(sys.argv) > 2 else 7)
START_ID = 1001

# ------------------------------------------------------------------ value helpers
AR_FIRST = ["محمد", "أحمد", "محمود", "مصطفى", "عمر", "علي", "حسن", "إبراهيم", "يوسف", "خالد", "طارق", "كريم",
            "سارة", "منى", "مريم", "نهى", "إيمان", "أسماء", "رحاب", "هبة", "دينا", "شيماء", "فاطمة", "نورهان",
            "اسلام", "عبدالله", "عبدالرحمن", "شريف", "وائل", "هشام", "سامح", "رامي", "تامر", "ياسمين"]
AR_LAST = ["عبدالعزيز", "السيد", "محمد", "إبراهيم", "حسن", "عبدالفتاح", "الشافعي", "منصور", "فرج", "سليم",
           "عرفه", "متولي", "البدري", "الجمال", "عبدالحميد", "رضوان", "صالح", "حمدي", "شاهين", "النجار"]
EN_FIRST = ["MOHAMED", "AHMED", "MAHMOUD", "MOSTAFA", "OMAR", "ALI", "HASSAN", "IBRAHIM", "YOUSSEF", "KHALED",
            "TAREK", "KARIM", "SARA", "MONA", "MARIAM", "NOHA", "EMAN", "ASMAA", "REHAB", "HEBA", "DINA",
            "SHAIMAA", "FATMA", "NOURHAN", "ISLAM", "ABDALLAH", "SHERIF", "WAEL", "HISHAM", "SAMEH", "RAMY"]
EN_LAST = ["ABDELAZIZ", "ELSAYED", "MOHAMED", "IBRAHIM", "HASSAN", "ABDELFATTAH", "ELSHAFEI", "MANSOUR",
           "FARAG", "SELIM", "ARAFA", "METWALY", "ELBADRY", "ELGAMAL", "RADWAN", "SALEH", "HAMDY", "SHAHIN"]

def name_ar(k=None):
    k = k or R.choice([2, 3, 3, 4])
    return " ".join([R.choice(AR_FIRST)] + R.sample(AR_LAST, k - 1))

def name_en(k=None, case="upper"):
    k = k or R.choice([2, 3, 3, 4])
    n = " ".join([R.choice(EN_FIRST)] + R.sample(EN_LAST, k - 1))
    if case == "title": return n.title()
    if case == "vf":          # Vodafone Cash style: "Ashgan Y Hamid"
        p = n.title().split(); return " ".join([p[0], p[1][0]] + p[2:]) if len(p) > 2 else n.title()
    return n

def name_any(**kw): return name_ar() if R.random() < 0.55 else name_en(**kw)

def mask_name(n):
    """NBE outgoing InstaPay: first name in clear, the rest as first letter + asterisks."""
    p = n.split()
    return " ".join([p[0]] + [w[0] + "*" * (len(w) - 1) for w in p[1:]])

def phone(prefix=None): return (prefix or R.choice(["010", "011", "012", "015"])) + "".join(R.choice("0123456789") for _ in range(8))
def digits(k): return "".join(R.choice("0123456789") for _ in range(k))
def last4(): return digits(4)
def hex8(): return "".join(R.choice("0123456789abcdef") for _ in range(8))

def amount(lo=5, hi=20000, ints=0.5):
    """Log-uniform between lo and hi (small amounts are more common); `ints` = share of round amounts."""
    lo, hi = max(lo, 1), max(hi, lo + 1)
    v = math.exp(R.uniform(math.log(lo), math.log(hi)))
    if R.random() < ints:
        k = R.choice([1, 5, 10, 50, 100]) if v > 200 else 1
        v = round(v / k) * k
    else:
        v = round(v, 2)
    return float(max(v, 1))

def f2(v): return f"{v:.2f}"
def fc(v, dec=True): return f"{v:,.2f}" if dec else f"{v:,.0f}"
def fint(v): return f"{v:.0f}" if v == int(v) else f"{v:.2f}"

def when():
    d = dt.datetime(2026, 1, 1) + dt.timedelta(days=R.randrange(0, 320), minutes=R.randrange(0, 1440))
    return d

def iso(d, time=True): return d.strftime("%Y-%m-%dT%H:%M:00") if time else d.strftime("%Y-%m-%d")
MON = "JAN FEB MAR APR MAY JUN JUL AUG SEP OCT NOV DEC".split()

POS = ["CARREFOUR MAADI", "SPINNEYS ZAYED", "TALABAT EG", "UBER *TRIP", "Uber", "Talabat", "Breadfast",
       "NOON (INSTANT)", "KASHIERFast", "ASWAK FATHALLA", "SAOOD MARKET", "HYPERONE", "B.TECH NASR CITY",
       "ELSAHEL MOBIL", "METRO MARKET", "SEOUDI SUPERMARKET", "KHEIR ZAMAN", "OSCAR GRAND STORES",
       "ZARA CITY STARS", "MCDONALDS ZAMALEK", "KFC MAADI", "COSTA COFFEE", "STARBUCKS CFC", "Swvl",
       "inDrive", "Instashop", "El Ezaby Pharmacy", "Seif Pharmacy", "TOTALENERGIES 6OCT", "WATANIA FUEL",
       "IKEA CFC", "DECATHLON", "LC WAIKIKI", "ELABD PATISSERIE", "GOURMET EGYPT", "RABBIT MART"]
ONLINE = ["NETFLIX.COM", "APPLE.COM/US", "GOOGLE *YouTube", "SPOTIFY", "AMAZON EG", "OPENROUTER, INC",
          "FACEBK *K7RTZP2", "STEAMGAMES.COM", "ANGHAMI", "SHAHID VIP"]
FOREIGN = [("USD", 2, 120), ("EUR", 2, 90), ("SAR", 10, 400), ("AED", 10, 400), ("INR", 100, 3000)]
BRANCH_EN = ["BOSTAN BR", "MAADI BR", "HELIOPOLIS BR", "SMOUHA BR", "ZAYED BR", "NASR CITY BR", "DOKKI BR"]
BRANCH_AR = ["المعادي", "مصر الجديدة", "سموحة", "الشيخ زايد", "مدينة نصر", "الدقي", "المنصورة"]
ATM_EN = ["CFC MALL ATM", "MALL OF EGYPT ATM", "ARKAN PLAZA ATM", "DANDY MALL ATM", "SUN CITY ATM"]

def pos(): return R.choice(POS + ONLINE[:4])

# ------------------------------------------------------------------ record builder
def rec(sms, typ=None, amt=None, cur=None, fee=None, bal=None, merch=None, chan=None, when_=None, l4=None):
    if typ is None:
        e = dict(is_transaction=False, type=None, amount=None, currency=None, fee=None, balance_after=None,
                 merchant=None, channel=None, datetime=None, account_last4=None)
    else:
        if merch is not None: assert merch in sms, (merch, sms)
        e = dict(is_transaction=True, type=typ, amount=amt, currency=cur, fee=fee, balance_after=bal,
                 merchant=merch, channel=chan, datetime=when_, account_last4=l4)
    return sms, e

# ------------------------------------------------------------------ Vodafone Cash (VF-Cash) — verified
VF_TAIL = [
    " مع كل معاملة بفودافون كاش هتزود فرصتك انك تكسب جنيه دهب لست الحبايب ,حول، اشحن،جدد باقتك، وادفع فواتيرك علشان تزود فرصتك من خلال http://vf.eg/vfcash\n",
    "تابع كل مصروفاتك من تاريخ المعاملات على أبلكيشن أنا فودافون http://vf.eg/vfcash\n",
    "",
]
def vf_date(d): return d.strftime("%H:%M %y-%m-%d")          # real VF receipts: HH:MM YY-MM-DD

def vf_send():
    a = amount(10, 15000, ints=0.85); fee = R.choice([0, 0, 1, 1, 1, 5]); b = amount(0, 30000, ints=0); d = when(); p = phone()
    s = (f"تم تحويل {fint(a)} جنيه لرقم {p} مصاريف الخدمة {fee} جنيه رصيد حسابك فى فودافون كاش الحالي {f2(b)}.\n"
         f"تاريخ العملية: {vf_date(d)}\nرقم العملية: 019{digits(9)}\n{R.choice(VF_TAIL)}")
    return rec(s, "transfer_out", a, "EGP", float(fee), b, p, "wallet", iso(d), None)

def vf_recv():
    a = amount(10, 20000, ints=0.7); b = amount(a, a + 25000, ints=0); d = when(); n = name_ar() if R.random() < .35 else name_en(case="vf")
    s = (f"تم استلام مبلغ {R.choice([fint(a), f2(a)])} جنيه من رقم {phone()} المسجل بإسم {n} على رقم محفظتك  {phone('010')}.\n"
         f"رصيدك الحالي: {f2(b)} جنيه\nتاريخ العملية: {vf_date(d)}\nرقم العملية: 019{digits(9)}\n"
         f"تابع كل مصروفاتك من تاريخ المعاملات على أبلكيشن أنا فودافون http://vf.eg/vfcash\n")
    return rec(s, "transfer_in", a, "EGP", None, b, n, "wallet", iso(d), None)

def vf_recv_intl():
    a = amount(200, 20000, ints=0.4); b = amount(a, a + 20000, ints=0); d = when(); src = "002" + digits(11); l = last4()
    t = f"{d:%b} {d.day}, {d.year} {(d.hour % 12) or 12}:{d:%M:%S} {'PM' if d.hour >= 12 else 'AM'}"
    astr = f"{a:,.0f}" if a == int(a) else f"{a:,.2f}"
    s = f"{t}: Received EGP{astr} from {src} to Mobile Account Number {l}. Ref: 019{digits(9)} Available Balance: {f2(b)}"
    return rec(s, "transfer_in", a, "EGP", None, b, src, "wallet", iso(d), l)

def vf_withdraw():
    a = float(R.choice(range(100, 20000, 50))); b = amount(0, 20000, ints=0); d = when()
    tail = R.choice([" دلوقتي ولأول مرة تقدر تشحن أي كارت كهرباء بفودافون كاش من مكانك ,دوس على http://vf.eg/vfcash  واختار خدمة شحن كارت الكهرباء.", ""])
    s = (f"تم سحب {a:.1f} ج بنجاح. رصيد حسابك في فودافون  كاش الحالي {f2(b)} جنيه. "
         f"تاريخ العملية ‎{d.strftime('%d-%m-%y %H:%M')} رقم العملية 019{digits(9)}.{tail}")
    return rec(s, "atm_withdrawal", a, "EGP", None, b, None, "wallet", iso(d), None)

def vf_withdraw_request():
    return rec(f"تم طلب سحب مبلغ {R.choice(range(100, 20000, 50)):.1f} جنيه من حساب فودافون كاش. للتأكيد اطلب #1*9* وادخل الرقم السري. رقم العملية 621{digits(14)}.")

def vf_balance():
    d = when()
    return rec(f"رصيد حسابك فى فودافون كاش الحالي{f2(amount(0, 30000, 0))} جنيه؛ تاريخ العملية {vf_date(d)} رقم العملية019{digits(9)}.تابع كل مصروفاتك من تاريخ المعاملات على أبلكيشن أنا فودافون http://vf.eg/vfcash")

def vf_insufficient():
    return rec(f"لا يوجد رصيد كاف في حسابك. يمكنك تحويل {R.randrange(50, 9000)} جنية فقط بعد خصم {R.choice([1, 5, 15])} ج رسوم تحويل; رقم العملية 019{digits(9)}")

def vf_wrong_pin():
    return rec(f"الرقم السري غير صحيح برجاء اعادة المحاولة,لو ناسي الرقم السري كلم #12*9* رقم العملية 019{digits(9)}")

def vf_promo():
    return rec(R.choice([
        f"اشتري باقة النت من خلال فودافون كاش قبل آخر اليوم وإستمتع ب {R.choice([10, 20, 30])}% ميجابايتس إضافية على باقتك. لشراء باقتك من فودافون كاش إطلب #28*9*",
        f"مبروك كسبت {R.choice([100, 200, 400])} جنيه تستخدمها دقائق لفودافون و ميجابيتس ب20 قرش الوحدة. للاستمتاع بالعرض إطلب \n*365*92# \nقبل يوم آخر اليوم",
        f"كسبت {R.choice([30, 50, 80])} جنيه كاش باك تستخدمها دقائق لفودافون اوميجابيتس ب 20 قرش الوحدة! ادخل علي تطبيق انا فودافون http://vf.eg/vfcash او اطلب \n *365*90# \n قبل آخر اليوم للاستمتاع بالهدية.",
        f"كاش باك مضمون و تحويلاتك بجنيه! \nحول فلوس بفودافون كاش قبل 2026-{R.randrange(1, 12):02d}-{R.randrange(1, 28):02d} وليك 30 جنيه فلوس على محفظتك تستخدمها في خدمات فودافون كاش و تقدر تحول بجنيه لاي محفظة في مصر \nاطلب #888*9*",
        f" فاضلك {R.choice([1, 2, 3])} تحويلات لفودافون كاش ومصاريف 5 تحويلات هترجعلك تاني وكمان بعد كل تحويلة عليك هتكسب تحويلة علينا! \nللتحويل كلم #7*9* او زور http://vf.eg/vfcash?id=money_transfer",
        "بنفكرك إنك ليك تحويلة هدية بدون رسوم من فودافون كاش! \nللتحويل كلم #7*9* او زور  http://vf.eg/vfcash?id=money_transfer",
        f"مبروك كسبت {R.choice([30, 50])} جنيه كاش باك فلوس على محفظتك تستخدمها في خدمات فودافون كاش. \nللاستمتاع بالعرض إطلب \n*365*93# \nقبل 2026-{R.randrange(1, 12):02d}-{R.randrange(1, 28):02d} ",
    ]))

# ------------------------------------------------------------------ National Bank of Egypt (BanK-AlAhly) — verified
NBE_END = "للمزيد اتصل بـ 19623"
def md(d, sep="-"): return d.strftime(f"%m{sep}%d")             # NBE: month-day, no year

def nbe_ipn_in():
    a = amount(10, 25000, .5); d = when(); l = last4(); n = name_any()
    s = f"تم إضافة تحويل لحظي لحسابكم رقم {l} بمبلغ {f2(a)} جم من {n} رقم مرجعي {digits(12)} يوم {md(d)} الساعة {d:%H:%M} {NBE_END}"
    return rec(s, "transfer_in", a, "EGP", None, None, n, "instapay", None, l)

def nbe_ipn_out():
    a = amount(10, 25000, .5); d = when(); l = last4(); n = mask_name(name_any(k=R.choice([1, 2, 3, 4]))) if R.random() < .9 else R.choice(AR_FIRST)
    s = f"تم تنفيذ تحويل لحظي من حسابكم رقم {l} بمبلغ {f2(a)} جم إلى {n} رقم مرجعي {digits(12)} يوم {md(d)} الساعة {d:%H:%M} {NBE_END}"
    return rec(s, "transfer_out", a, "EGP", None, None, n, "instapay", None, l)

def nbe_ipn_in_card():
    a = amount(10, 20000, .6); d = when(); l = last4(); n = name_any()
    s = f"تم إضافة تحويل لحظي لبطاقتكم المنتهية بـ  {l} بمبلغ  {f2(a)}جم من {n} رقم مرجعي  {digits(12)}يوم {md(d)}الساعة {d:%H:%M} {NBE_END}"
    return rec(s, "transfer_in", a, "EGP", None, None, n, "instapay", None, l)

def nbe_ipn_in_prepaid():
    a = amount(10, 10000, .6); d = when(); n = name_en()
    s = f"تم إضافة تحويل لحظي لبطاقتكم مسبقة الدفع بمبلغ {f2(a)} جم من {n} رقم مرجعي {digits(12)} يوم {md(d)} الساعة {d:%H:%M} {NBE_END}"
    return rec(s, "transfer_in", a, "EGP", None, None, n, "instapay", None, None)

def nbe_instant_pay():
    a = amount(10, 5000, .3); d = when(); l = last4(); m = R.choice(POS[:20] + ["Nat Gas", "Beanos Cafe"])
    s = f"تم خصم مبلغ {f2(a)} جم لحظيا باستخدام (شبكة المدفوعات اللحظية) من حسابكم رقم {l} عند {m} يوم {md(d)} الساعة{d:%H:%M} مرجع التاجر {digits(10)} {NBE_END}."
    return rec(s, "debit", a, "EGP", None, None, m, "instapay", None, l)

def nbe_debit_card():
    a = amount(5, 8000, .3); b = amount(0, 50000, 0); d = when(); l = last4(); m = pos()
    if R.random() < .7:
        s = f"تم خصم {f2(a)}EGP من بطاقة الخصم المباشر رقم {l} عند {m} يوم {md(d, '/')} الساعه {d:%H:%M} المتاح {f2(b)} للمزيد إتصل ب 19623"
    else:   # no-spaces variant
        s = f"تم خصم {fint(a)} EGP من بطاقة الخصم المباشر رقم{l} عند{m} يوم{md(d, '/')} الساعة{d:%H:%M} المتاح{f2(b)}EGP للمزيد اتصل ب 19623"
    return rec(s, "debit", a, "EGP", None, b, m, "card", None, l)

def nbe_credit_card():
    a = amount(5, 8000, .4); lim = amount(500, 60000, 0); d = when(); l = last4(); m = pos()
    s = f"تم خصم {fint(a)} جم من بطاقة الائتمان رقم {l} عند {m} يوم {md(d)} الساعة {d:%H:%M} المتاح {f2(lim)} جم للمزيد اتصل ب 19623."
    return rec(s, "debit", a, "EGP", None, None, m, "card", None, l)

def nbe_atm():
    a = float(R.choice(range(100, 10001, 100))); b = amount(0, 50000, 0); d = when(); l = last4()
    s = f"تم خصم {f2(a)}EGP من بطاقة الخصم المباشر رقم {l} عند NBE ATM{digits(3)} يوم {md(d, '/')} الساعه {d:%H:%M} المتاح {f2(b)} للمزيد إتصل ب 19623"
    return rec(s, "atm_withdrawal", a, "EGP", None, b, None, "atm", None, l)

def nbe_ipn_returned():
    a = amount(10, 10000, .5); d = when(); l = last4()
    s = f"تم رد تحويل لحظي لحسابكم رقم {l} بمبلغ {f2(a)} جم رقم مرجعي {digits(12)} يوم {md(d)} الساعة {d:%H:%M} {NBE_END}"
    return rec(s, "credit", a, "EGP", None, None, None, "instapay", None, l)

def nbe_bank_in():
    a = float(R.randrange(500, 150000)); l = last4(); ref = f"{digits(3)}INTA{digits(6)}{''.join(R.choice('ABCDEFGH') for _ in range(3))}"
    s = (f"تم اضافه تحويل   EGP {a:.0f}   لحساب  {l}  مرجع  {ref}" if R.random() < .5 else
         f"تم اضافه تحويل  {a:.0f} EGP   لحساب  {l}  مرجع  {ref}")
    return rec(s, "credit", a, "EGP", None, None, None, "bank_transfer", None, l)

def nbe_branch_deposit():
    a = float(R.randrange(100, 100000, 50)); d = when(); l = last4()
    s = f"تم إيداع   {a:.0f}  جنيه مصرى بفرع {R.choice(BRANCH_AR)} بحساب {l} يوم {d:%m/%d/%Y}"     # MM/DD/YYYY
    return rec(s, "credit", a, "EGP", None, None, None, "other", iso(d, False), l)

def nbe_dormancy():
    d = when()
    return rec(f"عملينا العزيز برجاء العلم أن حسابكم رقم {last4()} سيتم تركيده بتاريخ {d:%d/%m/%Y} ، ولتفادي تركيده يرجى إجراء أي من حركات سحب أو إيداع أو تحويل على الحساب قبل ذلك التاريخ من خلال أقرب فرع أو ماكينة صراف آلي أو قناة الكترونية متاحة.")

# ------------------------------------------------------------------ CIB — verified
CIB_END = "للمزيد، برجاء الاتصال بـ 19666"
def cib_ipn_out():
    a = amount(10, 30000, .5); d = when(); l = last4()
    s = f"يرجى العلم انه تم تنفيذ تحويل لحظي بمبلغ {f2(a)} جم من حسابك المنتهي بـ ********{l} برقم مرجعي {hex8()} بتاريخ {d:%d-%m-%Y %H:%M} {CIB_END} "
    return rec(s, "transfer_out", a, "EGP", None, None, None, "instapay", iso(d), l)

def cib_ipn_in():
    a = amount(10, 30000, .5); d = when(); l = last4(); n = name_en()
    s = f"يرجى العلم انه تم تنفيذ تحويل لحظي بمبلغ {f2(a)} جم إلى حسابك المنتهي بـ ********{l} من {n} برقم مرجعي {hex8()} بتاريخ {d:%d-%m-%Y %H:%M} {CIB_END}"
    return rec(s, "transfer_in", a, "EGP", None, None, n, "instapay", iso(d), l)

def cib_applepay():
    d = when(); l = last4(); m = pos()
    cur = "EGP" if R.random() < .8 else "USD"; a = amount(5, 6000 if cur == "EGP" else 150, .2); b = amount(0, 40000 if cur == "EGP" else 900, 0)
    s = f"تم خصم {cur} {f2(a)}  من بطاقة الخصم المباشر # **{l} باستخدام Apple Pay عند  {m} في  {d:%d/%m/%y %H:%M}الرصيد المتاح  {cur}{f2(b)}."
    return rec(s, "debit", a, cur, None, b, m, "card", iso(d), l)

def cib_card():
    d = when(); l = last4(); m = pos()
    if R.random() < .8: cur, a, b, bcur = "EGP", amount(5, 8000, .2), amount(0, 60000, 0), "EGP"
    else:
        cur, lo, hi = R.choice(FOREIGN); a = amount(lo, hi, .2); b = amount(0, 3000, 0); bcur = "USD"; m = R.choice(ONLINE)
    s = f"تم خصم مبلغ  {cur} {f2(a)} من بطاقة الخصم المباشر المنتهية بـ **{l} عند {m} في {d:%d/%m/%y %H:%M} ، الرصيد المتاح {f2(b)} {bcur}"
    return rec(s, "debit", a, cur, None, b, m, "card", iso(d), l)

def cib_atm():
    a = float(R.choice(range(100, 10001, 100))); b = amount(0, 50000, 0); d = when(); l = last4()
    s = f"تم سحب مبلغ  EGP {f2(a)}  من بطاقة الخصم المباشر المنتهية بـ **{l} من {' ' * R.randrange(1, 14)}{R.choice(ATM_EN)} في {d:%d/%m/%y %H:%M} ، الرصيد المتاح EGP {f2(b)}"
    return rec(s, "atm_withdrawal", a, "EGP", None, b, None, "atm", iso(d), l)

def cib_deposit():
    a = amount(100, 80000, .5); b = amount(a, a + 80000, 0); d = when(); l = last4()
    s = f"تم إيداع مبلغ {f2(a)} EGP  في CIB {R.choice(BRANCH_EN)} في بطاقتك المنتهية بـ **{l} بتاريخ {d:%d/%m/%y %H:%M} ،الرصيد المتاح {f2(b)} EGP"
    return rec(s, "credit", a, "EGP", None, b, None, "other", iso(d), l)

def cib_reversal():
    a = amount(5, 500, .5); b = amount(0, 20000, 0); l = last4(); m = R.choice(["Uber", "Talabat", "Breadfast", "inDrive", "Swvl"])
    s = f"تم اضافة المعاملة من {m} بقيمة {f2(a)} EGP إلى بطاقتك المنتهية بـ **{l} . الرصيد المتاح EGP {f2(b)}"
    return rec(s, "credit", a, "EGP", None, b, m, "card", None, l)

def cib_refund_order():
    a = amount(20, 5000, .3); d = when(); l = last4(); m = R.choice(["AMAZON EG ONLINE", "NOON ONLINE", "JUMIA EGYPT", "B.TECH ONLINE", "TALABAT MART"])
    s = f"تم اضافة المعاملة الخاصة بـ {m} على بطاقتكم المنتهية بـ {l} بقيمة EGP {f2(a)} بتاريخ {d:%d-%m-%Y} "
    return rec(s, "credit", a, "EGP", None, None, m, "card", iso(d, False), l)

def cib_refund_applepay():
    a = amount(20, 3000, .3); b = amount(0, 20000, 0); d = when(); l = last4(); m = R.choice(["Breadfast", "Talabat", "Instashop", "Rabbit"])
    s = f"تم اضافة المعاملة الخاصة بـ {m} على بطاقة# **{l} باستخدام Apple Pay بقيمة {f2(a)} EGP بتاريخ {d:%d/%m/%y} الرصيدالمتاح EGP {f2(b)}"
    return rec(s, "credit", a, "EGP", None, b, m, "card", iso(d, False), l)

def cib_cc_en():
    d = when(); l = last4()
    cur = "EGP" if R.random() < .8 else "USD"; a = amount(5, 9000 if cur == "EGP" else 200, .2); m = pos() if cur == "EGP" else R.choice(ONLINE)
    s = f"Your credit card ending with#{l} was charged for {cur} {fc(a)} at {m} on {d:%d/%m/%y}  at {d:%H:%M}. Card available limit is EGP  {f2(amount(100, 80000, 0))}. For more details, please visit https://cib.eg/mb"
    return rec(s, "debit", a, cur, None, None, m, "card", iso(d), l)

def cib_cc_refund_en():
    d = when(); l = last4(); m = R.choice(ONLINE); cur = R.choice(["USD", "EUR"]); a = round(R.uniform(0.1, 60), 2)
    at = f"{a:.2f}"[1:] if a < 1 else f"{a:.2f}"               # real: "EUR .93"
    s = f"The transaction on your credit card#{l}  from {m}  with {cur} {at} on {d:%d/%m/%y}  at {d:%H:%M} has been refunded. Please try again. Thank you"
    return rec(s, "credit", a, cur, None, None, m, "card", iso(d), l)

def cib_none():
    l = last4()
    return rec(R.choice([
        f"تم رفض المعاملة على بطاقتك المنتهية بـ **{l} من {R.choice(ONLINE + POS[:6])} بقيمة {f2(amount(20, 5000))} EGP لعدم كفاية الرصيد. الرصيد المتاح {f2(amount(0, 300, 0))} EGP",
        f"الرقم السري المتغير الخاص بعملية الشراء الالكترونية من  {R.choice(['Loop', 'Noon', 'Amazon', 'Talabat'])} لبطاقة رقم {l} بمبلغ EGP {f2(amount(20, 5000))} و سينتهي صلاحيته خلال10  دقائق. يرجي عدم مشاركة هذا الرقم مع أي شخص لأي سبب. OTP: {digits(6)}",
        f"عميل CIB العزيز، احصل على عائد مميز على وديعة لأجل {R.choice([12, 24, 36])} شهرًا بالجنيه المصري، تُصرف شهريًا وتبدأ من {R.choice([5000, 10000])} جم. تطبق الشروط والأحكام.",
        f"عميلنا العزيز، تم إضافة بطاقة  CIBالتي تنتهى برقم {l} بنجاح الىApple Wallet ، يمكنك الآن الاستمتاع ب Apple Pay باستخدام بطاقة CIB. تطبق الشروط و الأحكام",
        f"Your CIB OTP is {digits(6)}. Do not share this code with anyone. Valid for 5 minutes.",
    ]))

# ------------------------------------------------------------------ HSBC Egypt — verified
HSBC_END = "For further details, please contact HSBC call centre"
def hsbc_acct(): return f"074-{digits(3)}***-{digits(3)}"
def hsbc_day(d): return f"{d:%d}{MON[d.month - 1]}{d:%y}"          # 31AUG26

def hsbc_cc():
    d = when(); l = last4(); cur = "EGP" if R.random() < .8 else "USD"
    a = amount(5, 9000 if cur == "EGP" else 200, .3); m = R.choice(POS + ["kheir market", "NOON (INSTANT)", "APPLE.COM/US"]) if cur == "EGP" else R.choice(ONLINE)
    s = f"Your Credit Card ending with *** {l} has been used for {cur} {f2(a)} on {d:%d/%m/%Y} at {m}. Your available limit is EGP {f2(amount(100, 120000, 0))}"
    return rec(s, "debit", a, cur, None, None, m, "card", iso(d, False), l)

def hsbc_ipn(kind):
    a = amount(10, 50000, .4); d = when(); l = last4()
    if kind == "in":
        h = f"{R.choice(EN_FIRST).lower()}.{R.choice(EN_LAST).lower()}{R.choice(['', str(R.randrange(1, 99))])}@instapay"
        s = f"Your HSBC Account ********{l} was credited with IPN inward transfer for EGP {fc(a)} on {d:%d-%m-%Y %H:%M} from {h} with reference {hex8()}. {HSBC_END}"
        return rec(s, "transfer_in", a, "EGP", None, None, h, "instapay", iso(d), l)
    if kind == "out":
        n = name_en()
        s = f"Your HSBC Account ********{l} was debited with IPN outward transfer for EGP {fc(a)} on {d:%d-%m-%Y %H:%M} to {n} with reference {hex8()}. {HSBC_END}"
        return rec(s, "transfer_out", a, "EGP", None, None, n, "instapay", iso(d), l)
    if kind == "purchase":
        m = R.choice(["Nat Gas", "Beanos Cafe", "Talabat", "Gourmet Egypt", "Fawry Pay"]); a = amount(10, 4000, .2)
        s = f"Your HSBC Account ********{l} was debited with IPN purchase for EGP {fc(a)} on {d:%d-%m-%Y %H:%M} from {m} with reference {hex8()}. {HSBC_END}"
        return rec(s, "debit", a, "EGP", None, None, m, "instapay", iso(d), l)
    n = name_en()
    s = f"Your HSBC Account ********{l} was reversed with IPN outward transfer for EGP {fc(a)} on {d:%d-%m-%Y %H:%M} from {n} with reference {hex8()}. {HSBC_END}"
    return rec(s, "credit", a, "EGP", None, None, n, "instapay", iso(d), l)

def hsbc_line():
    d = when(); acct = hsbc_acct(); l = acct[-3:]; b = amount(0, 250000, 0)
    kind = R.choice(["charges", "ib", "atm", "purchase", "atm_dep", "atm_rev", "salary", "phone", "tt", "ccpay"])
    a = {"charges": float(R.choice([25, 50, 75, 100, 150])), "salary": amount(3000, 60000, .2)}.get(kind, amount(50, 60000, .3))
    m = None; sign = "-"
    if kind == "charges": desc, typ, ch = f"Charges from {acct}", "debit", "other"
    elif kind == "ib": desc, typ, ch = f"Internet Banking Transfer from {acct}", "transfer_out", "bank_transfer"
    elif kind == "atm": a = float(R.choice(range(500, 10001, 500))); desc, typ, ch = f"ATM Cash Withdrawal from {acct}", "atm_withdrawal", "atm"
    elif kind == "purchase":
        m = R.choice(["FAWRY*BEANOS", "CARREFOUR MAADI", "SPINNEYS", "KHEIR ZAMAN", "UBER *TRIP", "TALABAT"]); a = amount(20, 5000, .2)
        desc, typ, ch = f"{m} Purchase from {acct}", "debit", "card"
    elif kind == "atm_dep": desc, typ, ch, sign = f"ATM Cash Deposit to {acct}", "credit", "atm", "+"
    elif kind == "atm_rev": desc, typ, ch, sign = f"ATM Reversal of Cash Withdrawal from {acct}", "credit", "atm", "+"
    elif kind == "salary": desc, typ, ch, sign = f"Salary to {acct}", "credit", "bank_transfer", "+"
    elif kind == "phone": desc, typ, ch, sign = f"Phone Banking Transfer to {acct}", "transfer_in", "bank_transfer", "+"
    elif kind == "tt": desc, typ, ch, sign = f"TT Payment to {acct}", "credit", "bank_transfer", "+"
    else:
        s = f"From HSBC: {hsbc_day(d)} Transfer from {acct} EGP {fc(a)}- to your Credit Card ending with {last4()} as per your instruction. Your available balance is EGP {fc(b)}"
        return rec(s, "other", a, "EGP", None, b, None, "bank_transfer", iso(d, False), l)
    s = f"From HSBC: {hsbc_day(d)} {desc} EGP {fc(a)}{sign} Your available balance is EGP {fc(b)}"
    return rec(s, typ, a, "EGP", None, b, m, ch, iso(d, False), l)

def hsbc_cashback():
    a = amount(5, 600, 0); l = last4()
    s = f"You have earned Cashback of EGP {f2(a)} credited to your card ending with *** {l}.Check your statement or log on to Online Banking for details."
    return rec(s, "credit", a, "EGP", None, None, None, "card", None, l)

def hsbc_none():
    l = last4(); d = when()
    return rec(R.choice([
        f"A refund of USD {f2(amount(2, 100, 0))} from {R.choice(ONLINE)} on card *** {l} should be credited within 30 days. Call HSBC Contact center for queries.",
        "Enjoy up to 12 months installment plans at discounted interest rate & no processing fees for purchases of EGP 5000 or more with HSBC Credit Card. Call 19007 to place your request. T&Cs apply",
        f"Use PIN {digits(6)} to pay EGP {f2(amount(20, 5000))} at {R.choice(POS)} with HSBC card ending {l}. Call the number on the card's back if you didn't do this transaction. T&C apply",
        f"Transaction EGP {f2(amount(20, 5000))} on Card ending *** {l} was declined due to invalid PIN. Enter the correct PIN or call the number at the back of your Card to reset it.",
        "From HSBC: This is to notify you that your transaction via HSBC Online/Mobile Banking was  not successful. Kindly contact us for further details.",
        f"HSBC Credit Card ending *** {l} Statement Date {d:%d/%m/%Y}. Total Amt Due EGP {fc(amount(1000, 90000, 0))}, Due Date {(d + dt.timedelta(days=25)):%d/%m/%Y}. Min. Amt Due EGP {fc(amount(100, 5000, 0))}. Please ignore if paid.",
    ]))

# ------------------------------------------------------------------ Banque Misr — verified (real messages, numbers changed)
BM_LINK = "bnkmsr.com/online"
def bm_cc_glued():
    d = when(); l = last4(); cur = "EGP" if R.random() < .75 else R.choice(["USD", "EUR"])
    a = amount(5, 9000, .5) if cur == "EGP" else round(R.uniform(1, 150), 1)
    m = R.choice(["HK STORES", "FACEBK *K7RTZP2", "OPENROUTER, INC", "NETFLIX.COM", "CARREFOUR MAADI", "TALABAT", "SPINNEYS"])
    desc = m.ljust(22) + R.choice(["SP", "NE", "LU", "EG", "CA"])
    s = (f"عميلناالعزيز،شكرًا لاستخدامكم بطاقة بنك مصر الائتمانية*{l} تم خصم مبلغ {cur} {fint(a)} في{desc}بتاريخ {d:%d/%m/%Y}"
         f"،الرصيدالمتاحEGP {f2(amount(100, 300000, 0)).rstrip('0').rstrip('.')}،وحدالاستخدام الدولي المتاحEGP{f2(amount(100, 150000, 0)).rstrip('0').rstrip('.')}للمزيداتصل 19888")
    return rec(s, "debit", a, cur, None, None, m, "card", iso(d, False), l)

def bm_cc_spaced():
    d = when(); l = last4(); a = amount(5, 9000, .6)
    m = R.choice(["WE-Mobile-Pre", "GEIDEAE*Elmostafa mall", "AmanPF*Shadia Pharmacy", "TALABAT", "Paymob*Breadfast", "FAWRY*Electricity"])
    pad = R.choice([" ", "  >", " >", "          Gi"])
    bal = f" الرصيدالمتاحEGP {f2(amount(100, 300000, 0))}،" if R.random() < .8 else "،"
    s = f"عميلنا العزيز، شكرًا لاستخدامكم بطاقة بنك مصر الائتمانية *{l}، تم خصم مبلغ EGP {fint(a)} في {m}{pad} بتاريخ {d:%d/%m/%Y}،{bal} للاطلاع  اضغط على {BM_LINK}"
    return rec(s, "debit", a, "EGP", None, None, m, "card", iso(d, False), l)

def bm_debit_atm(deposit=False):
    a = float(R.choice(range(500, 30001, 500))); b = amount(0, 200000, 0); d = when(); l = last4()
    atm = f"الة رقم {digits(8)} BM {R.choice(['F.D SMA', 'HELIOPOLIS', 'TAHRIR', 'MAADI'])} يوم  {d:%d/%m}"
    if deposit:
        s = f"شكرًا لاستخدامك بطاقة بنك مصر ****{l}، تم إضافة مبلغEGP {f2(a)} {atm}، الرصيد المتاح EGP {f2(b)}لمزيد من المعلومات اضغط هنا {BM_LINK}"
        return rec(s, "credit", a, "EGP", None, b, None, "atm", None, l)
    s = f"شكرًا لاستخدامك بطاقة بنك مصر ****{l} ، تم الخصم مبلغEGP {f2(a)}  {atm} ، الرصيد المتاحEGP {f2(b)}لمزيد من المعلومات اضغط هنا {BM_LINK}"
    return rec(s, "atm_withdrawal", a, "EGP", None, b, None, "atm", None, l)

def bm_ipn_in_card():
    a = float(R.randrange(50, 20000, 50)); d = when(); l = last4(); n = name_en()
    s = f"تم إضافة تحويل لحظي الي بطاقة رقم {digits(6)}******{l} بمبلغ {a:.0f} من {n} رقم مرجعي {digits(6)} يوم {d:%d/%m/%Y} الساعه {d:%H:%M} للمزيد اتصل علي 19888"
    return rec(s, "transfer_in", a, None, None, None, n, "instapay", iso(d), l)

def bm_ipn_out():
    a = float(R.randrange(50, 20000, 50)); d = when(); acct = digits(16); n = name_en()
    s = f"تم تنفيذ تحويل لحظي من حسابكم رقم {acct} بمبلغ {a:.0f} جم إلى {n} رقم مرجعي {digits(6)} يوم {d:%d/%m/%Y} الساعه {d:%H:%M} للمزيد اتصل ب 19888"
    return rec(s, "transfer_out", a, "EGP", None, None, n, "instapay", iso(d), acct[-4:])

def bm_acct(kind):
    d = when(); l = last4(); dd = f"{d:%d}-{MON[d.month - 1]}-{d:%Y}"
    if kind == "deposit":
        a = float(R.randrange(100, 100000, 100))
        return rec(f"تم ايداع مبلغ {a:.0f}EGP فى حساب رقم xxx{l} فى {d:%d/%m/%Y}", "credit", a, "EGP", None, None, None, "other", iso(d, False), l)
    if kind == "in":
        a = float(R.randrange(50, 50000, 10))
        return rec(f"تم اضافة مبلغ {a:.0f}EGP       الى حساب رقم xxx{l}      فى {dd}  عن طريق التحويل اللحظي",
                   "transfer_in", a, "EGP", None, None, None, "instapay", iso(d, False), l)
    a = float(R.randrange(100, 100000, 100))
    return rec(f"تم تحويل مبلغ {a:,.0f}EGP     من حساب رقم xxx{l}       فى {dd}  عن طريق التحويل اللحظي",
               "transfer_out", a, "EGP", None, None, None, "instapay", iso(d, False), l)

def bm_refund():
    a = float(R.randrange(20, 5000)); d = when(); l = last4(); m = R.choice(["Uber", "Talabat", "Noon", "Amazon"])
    s = f"عميلنا العزيز، تم رد المعاملة بقيمة {a:.0f}EGP للبطاقة *****{l}، بتاريخ {d:%d/%m/%Y} من {m} ، للاطلاع على معاملاتكم اضغط {BM_LINK}"
    return rec(s, "credit", a, "EGP", None, None, m, "card", iso(d, False), l)

def bm_cc_payment():
    a = amount(500, 60000, 0); d = when(); l = last4()
    s = f"عميلنا العزيز، تم إيداع EGP {f2(a)} بالبطاقة الائتمانية المنتهية بـ ****{l}، فى BM-Online يوم  {d:%d/%m/%Y} ، ورصيدكم الحالي {f2(amount(1000, 300000, 0))} EGP، للاطلاع على معاملاتكم اضغط {BM_LINK}"
    return rec(s, "other", a, "EGP", None, None, None, "card", iso(d, False), l)

def bm_none():
    l = last4(); d = when()
    return rec(R.choice([
        f"عميلنا العزيز، برجاء عدم الافصاح عن الكود OTP: {digits(5)} الصالح لمره واحدة لإتمام معاملة الدفع بمبلغ EGP {f2(amount(20, 5000))} من {R.choice(['WAFFARHA', 'NOON', 'TALABAT'])} بطاقة رقم xxxx-xxxx-xxxx-{l}",
        f"Dear customer, your card ****{l} statement is issued with total EGP {f2(amount(500, 90000, 0))}, minimum due is EGP {f2(amount(100, 5000, 0))}, due before {d:%d/%m/%Y}",
        f"عميلنا العزيز، تم رفض العملية بالبطاقة ****{l} لتجاوز حد الاستخدام الدولي ،  الرصيد المتاح بالبطاقة EGP {R.randrange(1000, 300000)}",
        f"تم تسجيل الدخول علي حساب الانترنت البنكي الخاص بكم {d:%d-%m-%Y %H:%M:%S}",
    ]))

# ------------------------------------------------------------------ Orange Cash
ORANGE_ADS = [   # first one is a real ad from a real receipt; the rest follow its style
    "عرض مايتفوتش!\nوفّر 540 جنيه على اشتراك Yango Play واتفرج على اجمد الافلام والمسلسلات في مصر\nخصم 65% على اشتراك 6 شهور بـ300 جنيه بدل 840 جنيه\nادفع دلوقتي باورنچ كاش\nhttps://myo.orange.eg/YANGO",
    "ادفع فواتيرك باورنچ كاش واكسب 10% كاش باك لحد 50 جنيه\nhttps://myo.orange.eg/cash",
    "حوّل لأي محفظة أو حساب بنكي عن طريق انستاباي من اورنچ كاش\nhttps://myo.orange.eg/cash",
]
ORANGE_END = "+لأي استفسار كلم 7770 \nأو تواصل معانا على الواتساب: https://myo.orange.eg/O-whatsapp"

def oc_recharge():                                               # verified
    a = float(R.choice([10, 15, 20, 25, 50, 70, 100, 135, 200, 270, 300])); b = amount(0, 3000, 0); p = phone("012")
    ad = R.choice(ORANGE_ADS) if R.random() < .7 else ""
    s = f"تم شحن بنجاح لرقم {p} بقيمة {f2(a)}، رصيدك الحالي {f2(b)} جنيه، رقم المعاملة {digits(12)}." + (f"\n\n{ad}\n\n{ORANGE_END}" if ad else "")
    return rec(s, "bill_payment", a, None, None, b, p, "wallet", None, None)

def oc_send():                                                   # approximate
    a = amount(10, 10000, .8); fee = R.choice([0, 1, 1, 5]); b = amount(0, 20000, 0); p = phone(); d = when()
    s = f"تم تحويل {fint(a)} جنيه بنجاح لرقم {p}، مصاريف الخدمة {fee} جنيه، رصيدك الحالي {f2(b)} جنيه، رقم المعاملة {digits(12)}، بتاريخ {d:%d/%m/%Y %H:%M}."
    return rec(s, "transfer_out", a, "EGP", float(fee), b, p, "wallet", iso(d), None)

def oc_recv():                                                   # approximate
    a = amount(10, 10000, .8); b = amount(a, a + 20000, 0); n = name_ar() if R.random() < .5 else name_en(case="title")
    s = f"تم استلام {fint(a)} جنيه من رقم {phone()} المسجل باسم {n}، رصيدك الحالي {f2(b)} جنيه، رقم المعاملة {digits(12)}."
    return rec(s, "transfer_in", a, "EGP", None, b, n, "wallet", None, None)

def oc_bill():                                                   # approximate
    a = amount(20, 3000, .3); b = amount(0, 10000, 0); biller = R.choice(["فاتورة الكهرباء", "فاتورة الغاز", "فاتورة المياه", "WE Internet", "فاتورة التليفون الأرضي"])
    s = f"تم دفع {f2(a)} جنيه لـ {biller} بنجاح، رصيدك الحالي {f2(b)} جنيه، رقم المعاملة {digits(12)}."
    return rec(s, "bill_payment", a, "EGP", None, b, biller, "wallet", None, None)

def oc_none():                                                   # approximate
    return rec(R.choice([
        f"كود التأكيد الخاص بعملية اورنچ كاش هو {digits(6)}. متديهوش لأي حد حتى لو قال إنه من اورنچ.",
        f"رصيد محفظة اورنچ كاش الحالي {f2(amount(0, 20000, 0))} جنيه.\n{ORANGE_END}",
        f"{R.choice(ORANGE_ADS[1:])}\n\n{ORANGE_END}",
        f"تعذر إتمام عملية التحويل لعدم كفاية الرصيد. رصيدك الحالي {f2(amount(0, 200, 0))} جنيه.",
    ]))

# ------------------------------------------------------------------ e& cash / WE Pay / InstaPay / valU / Fawry — approximate
def eand_send():
    a = amount(10, 10000, .8); b = amount(0, 20000, 0); p = phone()
    s = f"تم تحويل {fint(a)} جنيه لرقم {p} بنجاح. رصيدك الحالي في e& cash {f2(b)} جنيه. رقم العملية {digits(10)}"
    return rec(s, "transfer_out", a, "EGP", None, b, p, "wallet", None, None)

def eand_recv():
    a = amount(10, 10000, .8); b = amount(a, a + 20000, 0); p = phone()
    s = f"تم استلام {fint(a)} جنيه من رقم {p}. رصيدك الحالي في e& cash {f2(b)} جنيه. رقم العملية {digits(10)}"
    return rec(s, "transfer_in", a, "EGP", None, b, p, "wallet", None, None)

def wepay_send():
    a = amount(10, 8000, .8); b = amount(0, 15000, 0); p = phone()
    s = f"WE Pay: تم تحويل مبلغ {fint(a)} جنيه إلى رقم {p}. رصيدك الحالي {f2(b)} جنيه. رقم العملية {digits(10)}"
    return rec(s, "transfer_out", a, "EGP", None, b, p, "wallet", None, None)

def wepay_recv():
    a = amount(10, 8000, .8); b = amount(a, a + 15000, 0); p = phone()
    s = f"WE Pay: تم استلام مبلغ {fint(a)} جنيه من رقم {p}. رصيدك الحالي {f2(b)} جنيه. رقم العملية {digits(10)}"
    return rec(s, "transfer_in", a, "EGP", None, b, p, "wallet", None, None)

def instapay_none():
    return rec(R.choice([
        f"Your InstaPay verification code is {digits(6)}. Do not share it with anyone.",
        f"كود التفعيل الخاص بتطبيق InstaPay هو {digits(6)} لا تشاركه مع أي شخص",
        f"{name_en(2, 'title')} requested EGP {f2(amount(20, 3000))} from you on InstaPay. Open the app to accept or decline.",
    ]))

def valu_purchase():
    a = amount(500, 60000, .7); n = R.choice([3, 6, 9, 12, 18, 24]); m = R.choice(["B.TECH", "Noon", "Amazon", "2B Computer", "Raya Shop", "IKEA"])
    s = f"valU: تم شراء بمبلغ {fint(a)} جنيه من {m} على {n} شهر، القسط الشهري {f2(a / n * 1.2)} جنيه."
    return rec(s, "debit", a, "EGP", None, None, m, "other", None, None)

def valu_none():
    d = when()
    return rec(f"valU: تذكير بموعد سداد القسط بقيمة {f2(amount(200, 5000, 0))} جنيه المستحق يوم {d:%d/%m/%Y}. ادفع من التطبيق أو أي منفذ فوري.")

def fawry_bill():
    a = amount(20, 3000, .3); d = when(); biller = R.choice(["WE Internet", "Electricity", "Vodafone Bill", "Natural Gas"])
    s = f"Fawry: Payment of EGP {f2(a)} for {biller} bill successful on {d:%d/%m/%Y}. Ref {digits(9)}"
    return rec(s, "bill_payment", a, "EGP", None, None, biller, "other", iso(d, False), None)

# ------------------------------------------------------------------ template table
T = [  # (template_id, sender, provenance, weight, fn)
    ("vf_send", "VF-Cash", "verified", 6, vf_send), ("vf_recv", "VF-Cash", "verified", 6, vf_recv),
    ("vf_recv_intl", "VF-Cash", "verified", 2, vf_recv_intl), ("vf_withdraw", "VF-Cash", "verified", 2, vf_withdraw),
    ("vf_withdraw_request", "VF-Cash", "verified", 1, vf_withdraw_request), ("vf_balance", "VF-Cash", "verified", 1.5, vf_balance),
    ("vf_insufficient", "VF-Cash", "verified", 1, vf_insufficient), ("vf_wrong_pin", "VF-Cash", "verified", .7, vf_wrong_pin),
    ("vf_promo", "VF-Cash", "verified", 4, vf_promo),
    ("nbe_ipn_in", "BanK-AlAhly", "verified", 5, nbe_ipn_in), ("nbe_ipn_out", "BanK-AlAhly", "verified", 4, nbe_ipn_out),
    ("nbe_ipn_in_card", "BanK-AlAhly", "verified", 1.5, nbe_ipn_in_card), ("nbe_ipn_in_prepaid", "BanK-AlAhly", "verified", 1, nbe_ipn_in_prepaid),
    ("nbe_instant_pay", "BanK-AlAhly", "verified", 1.5, nbe_instant_pay), ("nbe_debit_card", "BanK-AlAhly", "verified", 3, nbe_debit_card),
    ("nbe_credit_card", "BanK-AlAhly", "verified", 2, nbe_credit_card), ("nbe_atm", "BanK-AlAhly", "verified", 1.5, nbe_atm),
    ("nbe_ipn_returned", "BanK-AlAhly", "verified", .7, nbe_ipn_returned), ("nbe_bank_in", "BanK-AlAhly", "verified", 1, nbe_bank_in),
    ("nbe_branch_deposit", "BanK-AlAhly", "verified", .8, nbe_branch_deposit), ("nbe_dormancy", "BanK-AlAhly", "verified", .5, nbe_dormancy),
    ("cib_ipn_out", "CIB", "verified", 3, cib_ipn_out), ("cib_ipn_in", "CIB", "verified", 3, cib_ipn_in),
    ("cib_applepay", "CIB", "verified", 2, cib_applepay), ("cib_card", "CIB", "verified", 3, cib_card),
    ("cib_atm", "CIB", "verified", 1.2, cib_atm), ("cib_deposit", "CIB", "verified", 1, cib_deposit),
    ("cib_reversal", "CIB", "verified", 1, cib_reversal), ("cib_refund_order", "CIB", "verified", .8, cib_refund_order),
    ("cib_refund_applepay", "CIB", "verified", .6, cib_refund_applepay), ("cib_cc_en", "CIB", "verified", 2, cib_cc_en),
    ("cib_cc_refund_en", "CIB", "verified", .6, cib_cc_refund_en), ("cib_none", "CIB", "verified", 3, cib_none),
    ("hsbc_cc", "HSBC", "verified", 2, hsbc_cc), ("hsbc_ipn_in", "HSBC", "verified", 1.2, lambda: hsbc_ipn("in")),
    ("hsbc_ipn_out", "HSBC", "verified", 1.2, lambda: hsbc_ipn("out")), ("hsbc_ipn_purchase", "HSBC", "verified", .8, lambda: hsbc_ipn("purchase")),
    ("hsbc_ipn_reversed", "HSBC", "verified", .4, lambda: hsbc_ipn("rev")), ("hsbc_line", "HSBC", "verified", 4, hsbc_line),
    ("hsbc_cashback", "HSBC", "verified", .5, hsbc_cashback), ("hsbc_none", "HSBC", "verified", 2.5, hsbc_none),
    ("bm_cc_glued", "Banque Misr", "verified", 2.5, bm_cc_glued), ("bm_cc_spaced", "Banque Misr", "verified", 2, bm_cc_spaced),
    ("bm_debit_atm", "Banque Misr", "verified", 1.2, bm_debit_atm), ("bm_debit_atm_deposit", "Banque Misr", "verified", .6, lambda: bm_debit_atm(True)),
    ("bm_ipn_in_card", "Banque Misr", "verified", 1.2, bm_ipn_in_card), ("bm_ipn_out", "Banque Misr", "verified", 1.2, bm_ipn_out),
    ("bm_deposit", "Banque Misr", "verified", .7, lambda: bm_acct("deposit")), ("bm_ipn_in_acct", "Banque Misr", "verified", 1, lambda: bm_acct("in")),
    ("bm_ipn_out_acct", "Banque Misr", "verified", 1, lambda: bm_acct("out")), ("bm_refund", "Banque Misr", "verified", .7, bm_refund),
    ("bm_cc_payment", "Banque Misr", "verified", .6, bm_cc_payment), ("bm_none", "Banque Misr", "verified", 2, bm_none),
    ("oc_recharge", "Orange Cash", "verified", 3, oc_recharge),
    ("oc_send", "Orange Cash", "approximate", 2.5, oc_send), ("oc_recv", "Orange Cash", "approximate", 2.5, oc_recv),
    ("oc_bill", "Orange Cash", "approximate", 1, oc_bill), ("oc_none", "Orange Cash", "approximate", 2, oc_none),
    ("eand_send", "e& cash", "approximate", 1.2, eand_send), ("eand_recv", "e& cash", "approximate", 1.2, eand_recv),
    ("wepay_send", "WE Pay", "approximate", .8, wepay_send), ("wepay_recv", "WE Pay", "approximate", .8, wepay_recv),
    ("instapay_none", "InstaPay", "approximate", 1.5, instapay_none),
    ("valu_purchase", "valU", "approximate", 1, valu_purchase), ("valu_none", "valU", "approximate", .8, valu_none),
    ("fawry_bill", "Fawry", "approximate", 1, fawry_bill),
]

# Real inboxes are full of OTPs, promos, declines and notices; weight non-transactions to ~1/3 of the set
NON_TX = {"vf_withdraw_request", "vf_balance", "vf_insufficient", "vf_wrong_pin", "vf_promo", "nbe_dormancy", "cib_none",
          "hsbc_none", "bm_none", "oc_none", "instapay_none", "valu_none"}
NON_TX_BOOST = 2.4

if __name__ == "__main__":
    W = [t[3] * (NON_TX_BOOST if t[0] in NON_TX else 1) for t in T]
    rows, man = [], []
    for i in range(N):
        tid, sender, prov, _, fn = R.choices(T, weights=W)[0]
        sms, exp = fn()
        rid = START_ID + i
        rows.append({"id": rid, "sender": sender, "sms": sms, "expected": exp})
        man.append({"id": rid, "template_id": tid, "sender": sender, "provenance": prov})
    with open("sms_real_formats.jsonl", "w", encoding="utf-8") as f:
        for r in rows: f.write(json.dumps(r, ensure_ascii=False) + "\n")
    with open("manifest_real_formats.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["id", "template_id", "sender", "provenance"]); w.writeheader(); w.writerows(man)
    from collections import Counter
    print(len(rows), "messages;", Counter(m["sender"] for m in man))
    print(Counter(m["provenance"] for m in man), "| transactions:", sum(r["expected"]["is_transaction"] for r in rows))
