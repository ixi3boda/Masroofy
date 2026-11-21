# Real Egyptian bank & wallet SMS formats

`sms_real_formats.jsonl` holds 1,200 messages (ids 1001–2200) in the same schema as `sms_dataset_1000.jsonl`.
The wording, spacing and quirks are copied from real messages sent by Vodafone Cash, NBE, CIB, HSBC Egypt,
Banque Misr and Orange Cash. All names, phone numbers, card and account digits, references, amounts and
dates are synthetic, so no real person's data is in the file.

`manifest_real_formats.csv` has `id, template_id, sender, provenance` and works with your `evaluate.py`.

## Where the formats come from

There is no public dump of real Egyptian SMS (they are personal financial data). The formats below come
from open-source Egyptian expense-tracker / payment-gateway projects. These projects either published
device exports or kept real messages in their test fixtures with the numbers changed.

| Sender (SMS address) | Source | What it is |
|---|---|---|
| `VF-Cash` Vodafone Cash | [mahafez-app/sms_engine](https://github.com/mahafez-app/sms_engine) `data/*.json` | Real device export, 177 messages: send, receive, international receive, cash-out, cash-out request, balance, insufficient balance, wrong PIN, promos |
| `BanK-AlAhly` NBE | same export (21 messages), [Gallillio/mula](https://github.com/Gallillio/mula) `tests/fixtures/banks/nbe.ts`, [pennywiseai-tracker](https://github.com/sarim2000/pennywiseai-tracker) NBE tests, [paysync-gateway](https://github.com/Ziadtareks/paysync-gateway) tests | InstaPay in/out (account, card, prepaid card), instant payment at shop, debit & credit card, ATM, returned transfer, bank transfer in, branch deposit, dormancy notice |
| `CIB` | mula `cib.ts` (the fixture says "the wording and spacing are CIB's"), pennywiseai-tracker CIB tests, [Makromy/Motaaked](https://github.com/Makromy/Motaaked) tests | InstaPay in/out, Apple Pay, debit card, foreign card, ATM, deposit, hold reversal, refunds, English credit card + refund, decline, OTP, marketing |
| `HSBC` Egypt | mula `hsbc.ts`, [MoSaeedHammad/kippa](https://github.com/MoSaeedHammad/kippa) PR #1 tests | Credit card, IPN in/out/purchase/reversed, `From HSBC: 31AUG26 …` account lines (charges, IB transfer, ATM, deposit, salary, TT, card repayment), cashback, PIN, decline, statement |
| `Banque Misr` | kippa PR #1 tests, [Basta97/Flourish](https://github.com/Basta97/Flourish) fixtures (marked "Real messages (numbers, card digits and codes changed)") | Glued credit-card alerts (`فيHK STORES  SPبتاريخ`), spaced variant, debit-card ATM (`الة رقم`), InstaPay in/out, deposits, refunds, card repayment, OTP, statement |
| `Orange Cash` | [0XZEROX0/monthly-budget](https://github.com/0XZEROX0/monthly-budget) test script (a real recharge receipt) | Recharge receipt with the ad block appended |

`provenance` in the manifest:
- **verified** (1,032 messages): wording from the real messages above.
- **approximate** (168 messages): I found no real sample, so these copy the sender's style. They cover Orange Cash
  send/receive/bills/OTP, e& cash, WE Pay, InstaPay app notices, valU and Fawry. Replace them with your own
  messages (see below) before trusting their scores.

**InstaPay:** the InstaPay app does not send transaction SMS. The **bank** sends them as `تحويل لحظي`, `IPN` or
`شبكة المدفوعات اللحظية`. There are 265 InstaPay-channel messages, from NBE, CIB, HSBC and Banque Misr.

## Labelling conventions (same as your dataset)

- Credit-card "available" (`المتاح`, `الرصيدالمتاح`, `available limit`) is credit left, not a balance: `balance_after = null`.
  For debit cards and accounts it is the balance.
- `datetime` only when the text contains a full date. NBE writes `يوم 04-17` (month-day, **no year**), so it gets `null`.
  Use the SMS arrival time if you need it.
- Wallet transfer to a bare number: `merchant` = that phone number. When a name is given (`المسجل بإسم …`), the name.
- NBE masks the receiver: `merchant = "محمد ر**** ع*****"` exactly as written.
- HSBC accounts show three digits (`074-234***-001`): `account_last4 = "001"`.
- Card repayments (HSBC `to your Credit Card`, Banque Misr `تم إيداع … بالبطاقة الائتمانية`) are `type = "other"`.
- Not transactions: OTP/PIN, promos, statements, declines, failed transfers, cash-out **requests**
  (`تم طلب سحب … للتأكيد`), balance notices, refund-pending notices, dormancy notices, login alerts.

## What the real formats break in SmsTxnModel

Trained on your 1,000 fictional-sender messages and tested on these 1,200 (`cross_eval.py`):

| | your random split | your unseen_sender | **real formats** |
|---|---|---|---|
| tx F1 | 0.99 | 0.94 | **0.87** |
| non-transactions rejected | – | – | **0.66** |
| full record exact | 0.92 | 0.55 | **0.15** |
| merchant | 0.95 | 0.85 | **0.45** |
| balance_after | 1.00 | 0.87 | **0.76** |
| datetime | 1.00 | 1.00 | **0.86** |
| account_last4 | 1.00 | 0.94 | **0.76** |

Your `evaluate.py` run on the real-format set alone (`eval_real_only/`), so the model trains on real formats too:

| | random | unseen_wording | unseen_sender |
|---|---|---|---|
| tx F1 | 1.00 | 0.79 | 0.85 |
| full record exact | **0.61** | 0.21 | 0.10 |
| datetime | 0.83 | 0.94 | 0.89 |
| merchant | 0.88 | 0.63 | 0.53 |

Even the random split, where every template is seen in training, tops out at 0.61 full-record exact. The rule
layer (date regexes, number regex, tokenizer) can't represent several real formats, however much data it sees.

Causes, with the template where each shows up (all from `cross_eval_errors.json`):

1. **Date formats your rules don't know.**
   - Vodafone Cash `01:56 26-10-14` is `YY-MM-DD`, but it is read as 26 Oct **2014** (vf_recv datetime 0.05).
   - HSBC `31AUG26`, Banque Misr `30-AUG-2026`, Vodafone Cash `Feb 13, 2026 5:25:00 AM` and NBE branch `08/20/2026` (MM/DD) are not parsed at all.
2. **Currency glued to the number.** NBE `195.15EGP` becomes 195.0. Vodafone Cash `EGP15,608.48` and Banque Misr `11260EGP` / `مبلغEGP 9800` lose the amount, so the model grabs a phone or reference number instead (vf_recv_intl amount 0.00, bm_deposit 0.00).
   - Cause: `RE_NUM`'s `(?<![A-Za-z…])` / `(?![A-Za-z…])` rejects numbers that touch Latin letters.
   - The same thing drops CIB Apple Pay balances (`EGP209.69`, 0.00).
3. **`EUR .93`** (no leading zero, real CIB refund) is not a number candidate.
4. **Direction.** CIB writes `تم تنفيذ تحويل لحظي` for both incoming and outgoing transfers. Only `إلى حسابك` vs `من حسابك` differs, so every incoming CIB transfer is predicted `transfer_out` (type 0.00).
5. **Non-transactions with amounts get accepted:**
   - Vodafone Cash cash-out requests and "insufficient balance" messages
   - NBE dormancy notices (0% rejected)
   - HSBC statements and PIN messages
   - CIB e-commerce OTPs that state an amount
   - InstaPay payment requests
6. **Real transactions get rejected:**
   - Vodafone Cash sends (recall 0.56)
   - NBE `تم اضافه تحويل EGP …` (0.00)
   - HSBC `From HSBC:` lines (0.41)
   - Orange Cash recharge (0.14)
   - HSBC cashback (0.00)
7. **Merchant / counterparty (0.45):**
   - Vodafone Cash names after `المسجل بإسم` and bare phone numbers: 0.00
   - NBE masked names `ر****`: 0.00
   - Banque Misr glues Arabic to Latin (`فيNETFLIX.COM`). `WTOK` makes that one token, so the span can never be cut out. The tokenizer needs to split on Arabic/Latin script changes.
8. **account_last4:** NBE `لحسابكم رقم 6563` is missed (0.43), because `MASKED_RE` has no `رقم` cue.
9. **Credit-card limit read as balance:** NBE `بطاقة الائتمان … المتاح 1639.21` (0.00).
10. **Currency `ج`** alone (Vodafone Cash cash-out) is not in the lexicon.

Items 1–3 and 7 (tokenizer) are rule-layer limits: more training data will not fix them.

## Getting your own real messages

`import_my_sms.py` takes an Android export and:
- keeps finance senders only
- anonymizes names, phones, account/card digits, references and InstaPay handles, consistently within a run
- pre-labels each message with your model

```
python3 sms_model.py train sms_dataset_1000.jsonl model.joblib
python3 import_my_sms.py sms-backup.xml my_real_sms.jsonl model.joblib --start-id 5001
```

Export with the "SMS Backup & Restore" app (XML), or run
`adb shell content query --uri content://sms/inbox --projection address:body:date > inbox.txt`.
Correct every `expected` block by hand, because the pre-labels carry the errors above. Then remove `needs_review`.
The manifest groups messages by shape, so `unseen_wording` stays honest. Skim the output before you share it:
names in unusual positions can slip through the anonymizer.

## Files

- `gen_real_formats.py`: the generator (`python3 gen_real_formats.py 1200 7` reproduces the file)
- `cross_eval.py`: train on one dataset, test on another, broken down by sender / provenance / template
- `cross_eval_report.txt`, `cross_eval_results.json`, `cross_eval_errors.json`: the results above
- `eval_real_only/`: your `evaluate.py` run on the real-format set alone
- `import_my_sms.py`: export → anonymized, pre-labelled jsonl
