# Building and evaluating a REAL dataset

The 100 phrases in `phrases.jsonl` were written by the developer, so their scores are an upper bound.
This guide collects **real people describing real expenses in their own words**, labels them, and
produces honest numbers: WER/CER, per-field accuracy with 95% confidence intervals, precision, recall,
F1, the correction rate and latency.

## 1. Plan the collection

| | target |
|---|---|
| speakers | at least 10 (mix of men/women, ages, how much English they use) |
| recordings | 150+ in total, ~15 per speaker |
| language groups | ≥ 50 Arabic only, ≥ 50 mixed Arabic-English, ≥ 30 English |
| content | expenses they **really** made, said the way they normally talk, not read from a script |
| conditions | mix of quiet room, street, car, café; phone microphones are fine |

Franco-Arabic is a way of *writing*, so it doesn't exist in speech. To evaluate Franco, collect real
**typed** chat messages and evaluate them in text mode (step 6).

**Consent and privacy.** Tell people what the recordings are for, that only the team will hear them, and
that they can withdraw. Don't ask for names, card numbers or addresses. Delete anything personal from
the transcript. Recordings and labels stay out of git and out of the shared zip (both are excluded
already).

Message you can send (WhatsApp):
> أهلاً! بنعمل مشروع تخرج: تطبيق بتسجّل فيه مصاريفك بصوتك. ممكن لمدة أسبوع، كل ما تدفع حاجة، تبعتلي
> voice note قصيرة بتقول فيها اللي دفعته بطريقتك العادية (مثلاً "دفعت ٨٠ جنيه قهوة في سيلانترو الصبح").
> قول المبلغ والمكان لو فيه، وعادي تخلط عربي وإنجليزي. التسجيلات هتُستخدم بس لتقييم المشروع ومش هتتنشر،
> ومتقولش أي بيانات شخصية. شكراً جداً 🙏

## 2. Put the files in the project
Save each voice note (WhatsApp `.ogg`/`.opus`, `.m4a`, `.mp3` and `.wav` all work) into one folder per speaker:
```
eval/audio/collected/sara/note01.ogg
eval/audio/collected/sara/note02.ogg
eval/audio/collected/ahmed/...
```
Tip: on the phone, long-press the voice note → Share → save to Google Drive, then download it on the laptop.
Don't rename files from the same person to the same name.

## 3. Create the labelling sheet
```
python eval/make_label_sheet.py --audio-dir eval/audio/collected
```
→ `eval/dataset/real_labels.csv`. Open it in Excel. Run the command again whenever new files arrive;
it adds new rows and keeps your labels.

(`--prefill` fills the rows with the app's guesses to save time, but labellers then tend to accept wrong
guesses. **Don't use it for the numbers in the thesis.**)

## 4. Label every row (listen to the file first)

| column | what to write |
|---|---|
| `transcript` | exactly what was said. Arabic words in Arabic script, English words in English letters, **numbers as digits** ("150", not "مية وخمسين"), no punctuation needed |
| `lang_group` | `ar` (only Arabic words), `en` (only English), `mixed` (both) |
| `reference_time` | when it was recorded (the WhatsApp message time), e.g. `2026-11-25 18:30`. The sheet pre-fills the file's time — check it |
| `transaction_type` | `expense` or `income` |
| `amount` | the number, e.g. `1500` or `12.5`; empty if no amount was said |
| `currency` | `EGP` unless another currency was said (`USD`, `EUR`, `SAR`, `AED`, `GBP`) |
| `merchant` | shop/app/brand name in its usual spelling (`Uber`, `Carrefour`, `Cilantro`); empty if none |
| `category` | one of: `food_dining groceries transport fuel shopping electronics bills_utilities mobile_internet health education entertainment subscriptions housing personal_care gifts_donations travel income other` |
| `date` | the date of the expense, worked out from `reference_time` ("امبارح" recorded on 25/11 → `2026-11-24`); if no day was said, the recording date |
| `time` | only if a time was said: `15:00` for "الساعة 3 العصر". For only "الصبح / بالليل / العصر" write `09:00 / 21:00 / 16:00` and put `yes` in `time_word` |
| `payment_method` | `cash`, `card`, `wallet` (InstaPay, Vodafone Cash…) or `unknown` if not said |
| `checked` | `yes` when the row is finished — only checked rows are imported |
| `comment` | anything unclear (it isn't used for scoring) |

Label what the person **meant**, not what the app would output. If the person was unsure ("حوالي 200"),
label 200. Save as **"CSV UTF-8 (Comma delimited)"** so the Arabic isn't lost.

Quality check (recommended for the thesis): a second teammate independently labels 20% of the rows; report
the % of fields where the two labellers agree.

## 5. Import and validate
```
python eval/import_labels.py
```
It checks every row (unknown category, impossible date, missing file …) and prints the row number of each
problem. Fix the rows in Excel and run it again. Its output files are `eval/dataset/real.jsonl` and
`eval/dataset/real_manifest.csv`.

## 6. Get the numbers
```
# full system: speech-to-text + extraction  (THE main result)
python eval/evaluate.py --mode audio --dataset eval/dataset/real.jsonl --manifest eval/dataset/real_manifest.csv

# extraction only, on the human transcripts  (how much of the error comes from ASR?)
python eval/evaluate.py --mode text --dataset eval/dataset/real.jsonl

# Whisper language forced to Arabic vs automatic detection
python eval/evaluate.py --mode audio --dataset eval/dataset/real.jsonl --manifest eval/dataset/real_manifest.csv --compare
```
Each run writes `results/<time>/report.md` (all tables), `predictions.csv`, `errors.csv` and `confusion_category.csv`.

## 7. What to put in the thesis

1. **Dataset table**: number of recordings, speakers, per language group, total minutes, recording conditions.
2. **ASR**: WER and CER per language group.
3. **Extraction**: for amount, merchant, date and category: accuracy (95% CI), precision, recall, F1, per
   language group; plus micro-F1 over all fields and category macro-F1.
4. **Audio vs text**: the same metrics on the human transcripts (text mode). The difference is the error
   caused by speech recognition.
5. **Correction rate**: average fields to fix per transaction and % of transactions needing a fix (the
   proposal's metric). Add `python eval/confirmed_report.py` numbers if testers used the app.
6. **Latency**: p50 / p95 total and ASR time, real-time factor, model load time, on named hardware
   (e.g. "Core i5 laptop CPU, Whisper small int8").
7. **Error analysis**: 5–10 typical mistakes from `errors.csv` and why they happen.

With 150 examples, a 90% accuracy has a 95% interval of about ±5 points. Always report n next to every
percentage.
