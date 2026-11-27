# Decisions and assumptions

Every place where the brief left a choice open, what we chose and why.

## Numbers and money
- **"1,500" and "1.500" both mean 1500.** A comma or dot followed by exactly three digits (and 1–3 digits before it) is a thousands separator; with one or two digits after it it is a decimal ("12.50", "12,50"). Egyptian prices almost never have three decimals, while "1.500" for 1500 is common in Egyptian writing.
- **"k" = thousand** ("2.5k" = 2500) and **"m"/"million"** after a number = million.
- **Fractions** apply to the last scale word: "ألف ونص" = 1500, "مية ونص" = 150. After the currency word they mean half a pound: "عشرة جنيه ونص" = 10.50. "و خمسين قرش" after the currency adds 0.50. Piasters on their own are never the amount.
- **"تمن"** is only a number before a scale word ("تمن تلاف" = 8000); alone it means "the price of".
- **Choosing the amount** — every number is scored: next to a currency word +0.6, after ب/for +0.3, within four words after a pay verb +0.15; small word-numbers (≤ 10) without currency −0.25 ("واحد صاحبي"); year-like numbers −0.3. Numbers followed by quantity/duration units (كيلو, kg, days, pm...), after الساعة/at, next to a month name, inside a merchant name or followed by قرش are excluded. If the two best scores are within 0.15, confidence drops to 0.45 and `amount` goes to `needs_review`.
- **Amount in JSON** is a number with two decimals (e.g. `150.0`), stored internally as `Decimal`. Mobile developers find numbers easier than strings; inside Python we never use float maths on money.

## Currency
- Default **EGP** (confidence 0.7) when no currency is said.
- **GBP** only with استرليني / sterling / £ / gbp; this check runs before the generic "pound(s)" → EGP rule.
- "bucks" → USD, "quid" → GBP.
- The single letters "ج" and "LE" count as currency only right after a number.

## Dates and times (Africa/Cairo, explicit `now`)
- **Weekday names** mean the most recent occurrence that is not in the future; today counts ("يوم الجمعة" on a Friday = today). With "اللي فات / الماضي / last" the same weekday as today means 7 days ago. "last Thursday" on a Friday = yesterday (most recent), not the Thursday of the previous week. This is ambiguous in real speech, so weekday confidence is 0.8.
- **"5/11" is 5 November** (day/month, Egyptian convention). Four-digit first ("2026-11-05") is ISO.
- **Day + month without year** that would be in the future (e.g. "3 ديسمبر" said in November) → previous year, because expenses are in the past.
- **"الأسبوع اللي فات" / "last week"** = now − 7 days, confidence 0.4, flagged. "last month" = now − 30 days, flagged.
- **بكرة / tomorrow** are parsed (+1 day) but flagged in `needs_review` (an expense in the future is suspicious).
- **Default times** for time-of-day words: الصبح/morning 09:00, الضهر/noon 13:00, العصر/afternoon 16:00, المغرب 18:00, المسا/evening 19:00, بالليل/night 21:00. These are conventions, so the evaluation accepts ±60 minutes for them.
- **"الساعة 3"** with no qualifier stays 03:00 and `time` is flagged. With بالليل/العصر/المغرب/مساء/pm it becomes PM; with الضهر hours 1–5 become PM; "الساعة 12 بالليل" = 00:00.
- No date mentioned → the reference date, confidence 0.7 (not flagged: most people log expenses the same day).

## Merchants
- **Gazetteer of 89 merchants** with Latin, Arabic-script and Franco aliases. Matching uses normalized, folded tokens; the first word may carry an attached prefix (فأوبر, بالفيزا, لوي).
- **Ambiguous aliases** (words that are also normal words: we/وي, total, orange, noon/نون, طلبات, كريم, سعودي, شاهد, فوري, مترو...) need a preposition right before them or a context word nearby. "Strict" ones (we, total, orange, noon, mobil, booking) need the context word right next to them or a specific preposition; "Total"/"Mobil" also match when capitalised mid-sentence after a preposition.
- **"مترو" = Metro Market, "المترو" = Cairo Metro** (as the brief says). English "metro" = Cairo Metro.
- **Fuzzy matching** (similarity ≥ 88) only for words of 3+ letters in the same script, never for stop words, category words, date words or pay verbs. Confidence 0.7.
- **Pattern** (unknown shop after في/من/عند/at/from/in/on) only when the gazetteer found nothing. Arabic-only spans need من/عند (after "في" Arabic words are usually places like "في البيت"). Confidence 0.5 and always flagged.

## Categories
- Precedence: explicit keyword (0.85, or 0.92 when it agrees with the merchant) > merchant default (0.75) > LLM guess (0.6) > "other" (0.3). Ties between keywords are broken by a per-category `priority` in categories.json (specific categories like health and fuel beat generic ones like bills or shopping) and lower the confidence to 0.65.
- "other" keywords (حاجات, stuff...) never beat a merchant default.
- **Income** is decided by the transaction type, not by a keyword: strong verbs (قبضت, اتحولي, received, got paid) → income; salary nouns (المرتب, salary) → income only if there is no pay verb ("دفعت مرتب البواب" is an expense).

## Payment method
- كاش/cash/نقدي → cash; فيزا/visa/mastercard/ميزة/credit/debit/apple pay → card; instapay/vodafone cash/etisalat cash/orange cash/we pay → wallet.
- Generic words "card/كارت/wallet/محفظة" need a hint before them (ب/by/with/my/paid...) because "اشتريت محفظة" means buying a wallet. "كارت شحن" and "كارت الكهربا" are not payment methods.

## Language field
- Word-level script check: only Arabic-script words → "ar", only Latin → "en", both → "mixed". Franco-Arabic is reported as "en" because the schema has only three values; the dataset keeps a separate "franco" group for evaluation.

## ASR
- **Default `ASR_LANGUAGE=ar`.** Whisper's language detection often picks English for code-switched Egyptian speech and then garbles the Arabic part. Forcing Arabic keeps Arabic words in Arabic script. `evaluate.py --mode audio --compare` measures ar vs auto so the team can confirm on real recordings.
- **Initial prompt** (`ASR_INITIAL_PROMPT`) is a short example in the mixed style we want: Western digits, Latin brand names inside Arabic ("دفعت 150 جنيه في Uber ..."). Whisper conditions on the previous text, so this nudges it to write "150" instead of "مية وخمسين" and "Uber" instead of "اوبر", which makes extraction easier.
- **CPU by default (`WHISPER_DEVICE=cpu`).** Many laptops have an NVIDIA GPU but not the CUDA 12/cuDNN libraries, and then Whisper crashes with "cublas64_12.dll not found". CPU works everywhere. Set `cuda` or `auto` on machines with CUDA installed (Colab). If a GPU run still fails because of missing libraries, the code retries on the CPU with a warning.
- **faster-whisper** is the default: no torch, int8 on CPU, float16 on GPU, `beam_size=5`, `vad_filter=True` (cuts silence, which also reduces hallucinations). The model is loaded once per process; load time is reported separately (`timings_ms.model_load`).
- **Mock sidecar naming**: `clip.wav` → `clip.txt` first, then `clip.wav.txt`.
- **Duration limit** 60 s (configurable). Durations are read with the built-in `wave` module for WAV and with soundfile for other formats when installed; otherwise the limit is checked after transcription using Whisper's own duration.

## LLM
- Default provider **none**: the project must work for free and offline.
- Default model for Anthropic: `claude-haiku-5-5` (small and fast; set `LLM_MODEL` to change). Default for openai_compatible: `gpt-4o-mini`; for Ollama set e.g. `LLM_MODEL=qwen2.5:7b`.
- In hybrid mode the LLM is called when the amount is missing, the category is "other", or any of amount/category/date/currency/merchant(if found) has confidence < `HYBRID_CONFIDENCE_THRESHOLD` (0.6).
- A merchant returned by the LLM is mapped to the canonical gazetteer name when possible; otherwise it is kept but flagged for review.
- Cache key: prompt version + provider + model + reference date + transcript (SHA-256). Turn off with `LLM_CACHE=0`.
- Hard timeout: the provider call runs in a worker thread and is abandoned after `LLM_TIMEOUT_S` (+1 s), in addition to the SDK's own timeout.

## Confidence and needs_review
- A field goes to `needs_review` when its confidence is below `REVIEW_CONFIDENCE_THRESHOLD` (0.6), when the amount is missing or ambiguous, when the merchant came from the pattern rule or from the LLM but is not in the gazetteer, when the date is vague or in the future, or when an explicit time had no AM/PM hint. A missing merchant is NOT flagged (many expenses have no shop).
- Confidence values are hand-set per rule (documented in the code), not learned. They are useful for ranking, not calibrated probabilities.

## Storage and API
- SQLite file `expenses.db` (configurable). `transactions` keeps the final values and the original draft JSON; `corrections` keeps one row per corrected field.
- `ConfirmRequest` = the draft exactly as returned + only the changed fields in `corrections`. A correction that does not really change the value (e.g. "150" vs 150.00) is not counted.
- A transaction cannot be saved without an amount (`422 amount_required`).
- CORS allows all origins for local development; restrict it before deployment.

## Evaluation
- Field rules: amount ±0.01; currency/category/type/payment exact; merchant canonical-name equality or token_set_ratio ≥ 85 for non-gazetteer names; date exact; time exact or ±60 min for time-of-day words.
- "Full record exact match" uses amount, currency, merchant, category, date.
- **Precision/recall/F1** use slot-filling scoring: TP = filled and correct; FP = filled but wrong, or filled when nothing was expected; FN = expected but empty or wrong (a wrong value is both FP and FN); TN = correctly empty. "unknown" payment method counts as empty. Category, transaction type and payment method also get a scikit-learn-style classification report (per class, macro, weighted) and the category confusion matrix.
- "Estimated correction rate" assumes the user fixes every wrong field among the 8 evaluated fields.
- The first item of every run is a warm-up and is not counted in latency statistics.
- The reference time for every dataset item is Friday 2026-11-20 14:00 (+02:00).
- **Honesty note:** `phrases.jsonl` was written while building the rules, so its text-mode accuracy is an upper bound. `challenge_unseen.jsonl` (30 phrases written afterwards, never used to tune the rules) is the more honest text-only check. Real recordings are the honest end-to-end check.

## Environment
- Python 3.10–3.12 (code avoids newer syntax; also tested on 3.13). Minimum versions are pinned, not exact versions.
- `tzdata` is in requirements.txt because Windows has no system timezone database.
- `python-multipart` is in requirements.txt because FastAPI needs it for file uploads.
- Fuzzy matching and WER fall back to pure-Python implementations of the same formulas if rapidfuzz/jiwer are missing.
