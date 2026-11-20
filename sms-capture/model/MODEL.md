# SMS transaction detector — Egyptian bank & wallet SMS

Detects whether an incoming SMS is a money transaction and extracts the fields of the dataset schema
(`type, amount, currency, fee, balance_after, merchant, channel, datetime, account_last4`).
Arabic, English and mixed; Arabic-Indic digits supported. Pure scikit-learn, CPU-only, ~2 MB model,
milliseconds per message, so it can run on-device or server-side.

## Files
- `sms_model.py` — the model (train / predict CLI + `SmsTxnModel` class)
- `sms_txn_model.joblib` — trained on all 1,000 synthetic messages (scikit-learn 1.9.1)
- `evaluate.py` — the three evaluation splits below; `eval_results.json` — the numbers

## Usage
```bash
python3 sms_model.py train   data.jsonl  sms_txn_model.joblib
python3 sms_model.py predict sms_txn_model.joblib "تم خصم مبلغ 250 جنيه من بطاقتكم ****1234 لدى ..."
python3 sms_model.py predict sms_txn_model.joblib --jsonl incoming.jsonl > predictions.jsonl
python3 evaluate.py sms_dataset_1000.jsonl manifest.csv
```
```python
from sms_model import SmsTxnModel
m = SmsTxnModel.load("sms_txn_model.joblib")
m.predict(sms_text)   # -> dict in the dataset's "expected" format, plus "_confidence"
```
Training only needs JSONL in the dataset schema, so the same command retrains on real labelled SMS.
Only load `.joblib` files you trust (they are pickles), and load with the same scikit-learn version.

## Design
| Stage | Method | Why |
|---|---|---|
| 0. Normalize | Arabic-Indic digits and ٬ ٫ separators → ASCII, one character for one, so text positions are kept | Same model sees `١٬٢٥٠٫٥٠` and `1,250.50` |
| 1. Transaction + type | TF-IDF char 2–5-grams + word 1–2-grams + **domain cue lexicon** → logistic regression over `none` + 7 types | Char n-grams absorb typos and Arabic morphology; the cue lexicon (خصم/سحب/debited vs إيداع/استلام/credited, OTP, promo, declined…) is what carries over to unseen banks |
| 2. Channel | Same features → logistic regression (transactions only) | |
| 3. Number roles | Every number is a candidate; logistic regression on its context labels it amount / fee / balance / last4 / other | Separates amount from balance, fee, card digits, refs, instalments; dates/times are masked first so `14.11.26` is never an amount |
| 4. Merchant | Per-token B/I/O logistic regression, ±2-token window + token classes (preposition, date-word, wallet/account word, currency); best span decoded | Handles Arabic and Latin names, persons, billers |
| 5. Rules | Date/time parser (dd/mm/yy, dd-mm-yyyy, dd.mm.yy, "12 Nov 2026", "12 نوفمبر 2026", AM/PM, ص/م); currency lexicon next to the amount; "no fee" phrases → fee 0 | Finite formats: rules are exact and need no data |

A predicted transaction with no number in it is rejected. `_confidence` is the type classifier's top probability:
route low-confidence messages (e.g. < 0.7) to review.

## Results (5-fold cross-validation on the 1,000 synthetic messages)
| Metric | Random split | Unseen wording | Unseen sender |
|---|---|---|---|
| Transaction F1 | 0.994 | 0.959 | 0.938 |
| Type | 0.985 | 0.870 | 0.928 |
| Amount | 1.000 | 1.000 | 1.000 |
| Currency | 1.000 | 1.000 | 1.000 |
| Fee | 1.000 | 0.997 | 0.987 |
| Balance after | 0.997 | 0.994 | 0.872 |
| Merchant | 0.950 | 0.888 | 0.843 |
| Channel | 0.991 | 0.939 | 0.869 |
| Datetime | 1.000 | 1.000 | 1.000 |
| Card/account last 4 | 0.997 | 0.957 | 0.925 |
| **All fields exactly right** | 0.924 | 0.652 | 0.538 |

Field accuracies are measured on transactions correctly detected. Splits:
- **Random** — the same templates appear in training and test. This is optimistic; treat it as an upper bound.
- **Unseen wording** — test messages use template wordings never seen in training (grouped by template).
- **Unseen sender** — leave-one-sender-out: the whole SMS format of that bank is new. This is the closest
  estimate of what happens when a new bank's messages arrive.

Unseen-sender notes: Sinai Pay scores 0 on "all fields" only because the dataset labels its bill channel
`unknown`, a convention no other sender teaches, so no model could learn it. Luxor Bank is the only sender
using `xx1234` masks and "Avl Bal", so it is the hardest to transfer to.

## Limits — read before using on real SMS
- Trained and tested only on synthetic, template-generated data. Real-world accuracy will be lower;
  the unseen-sender column is the best available estimate. Collect and label a few hundred real SMS
  (anonymised) per bank, retrain, and re-run `evaluate.py`.
- New phrasing can still slip through. In a spot check on 7 hand-written messages in new styles, 6 came out
  right; "EGP … spent on your Visa" was missed until "spent" and card-network names were added to the
  cue lexicon. Extending `LEX` in `sms_model.py` is the cheapest way to cover a new bank.
- Merchant boundaries are the weakest field (e.g. "KOSHK EL NADA CAFE" → "KOSHK EL NADA").
- With PyTorch available, a fine-tuned multilingual token-classification model (e.g. an Arabic-English
  BERT) trained on real labelled SMS would be the natural next step; keep the same evaluation splits.
