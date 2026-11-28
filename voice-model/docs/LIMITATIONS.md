# Known limitations and how to improve them

## 1. The text-mode numbers are optimistic
`eval/dataset/phrases.jsonl` (100 phrases) was written together with the rules, so the rules were shaped around these phrasings. On it the rules score close to 100%. On `challenge_unseen.jsonl` (30 new phrasings, never used for tuning) the first run gave 90% full-record exact match, with misses such as an unknown restaurant after "في مطعم", "City Stars" (a mall not in the list) and "Electricity card top-up" (classified as mobile top-up). Real users will say things neither set covers.
**Next step:** collect 200+ real sentences from the team and friends (typed and spoken), label them, and report on those.

## 2. Dialect and vocabulary coverage
Egyptian Arabic is covered best. Gulf/Levantine words, rare number forms, slang ("بكام", "بالشيء الفلاني"), and new brands are not.
**Next steps:** grow `categories.json` and `merchants.json` from the `corrections` table (every time a user fixes a merchant/category, that is a new alias or keyword); add a review screen for the team to approve suggested aliases.

## 3. TTS audio is not real speech
Synthetic voices are clean, slow and always pronounce numbers the same way. WER on TTS audio will be much lower than on real phone recordings in a noisy street.
**Next step:** record every team member with `eval/record_audio.py` (and a few people outside the team), in quiet and noisy places, and report those numbers in the final report.

## 4. Ambiguous numbers
"دفعت 50 و 30" (one amount or two?), "الساعة 3 دفعت 3 تلاف", "two coffees 190" are resolved by heuristics. Spoken numbers are also mis-transcribed by Whisper ("خمستاشر" vs "خمسطاشر", "تلتمية" written as "تلت مية"). When the rule is unsure, the amount is flagged — but some confident mistakes are not flagged (needs_review recall is not perfect).
**Next steps:** sum mode for "X و Y" when both have no currency; use the LLM in hybrid mode for low-confidence amounts; tune scores on real data.

## 5. Whisper hallucination on silence and noise
Whisper may invent text on silence ("ترجمة نانسي قنقر", "Thanks for watching"). We use VAD and remove known phrases, but new hallucinations can appear, and a hallucinated sentence could contain a number.
**Next steps:** reject clips with very low speech probability (faster-whisper segment `no_speech_prob`), and show the transcript prominently in the app so the user notices.

## 6. Code-switching inside ASR
Whisper forced to Arabic sometimes writes English brands in Arabic script ("أوبر", "كارفور") — handled by aliases — but may also translate English words ("groceries" → "بقالة") or drop them. Forcing English loses the Arabic.
**Next step:** fine-tune Whisper (small or medium) on the team's labeled recordings (even 1–2 hours helps a lot for a narrow domain), or try a model trained on Egyptian code-switched speech.

## 7. Confidence values are hand-set
They rank fields reasonably but are not calibrated probabilities.
**Next step:** after collecting corrections, fit a simple calibration (e.g. isotonic regression) per field.

## 8. Dates
"last Thursday" said on a Friday is ambiguous (yesterday or 8 days ago); we choose yesterday and do not flag it. Hijri dates, "أول الشهر", "يوم القبض" are not supported.

## 9. Merchants that are normal words
Short brand names that are also normal words ("we", "orange", "total", "نون") need context. Some real uses will be missed ("دفعت لنون 300" is matched, "نون 300" is not).

## 10. Storage and security
SQLite and open CORS are for development only. There is no user authentication; every confirmed transaction goes to one table. The real backend must add users, auth and HTTPS.

## 11. Mobile deployment
Running Whisper on a server costs money and needs the network.
**Next step:** an on-device model for the mobile app (e.g. whisper.cpp / a quantized Whisper tiny/base fine-tuned on our data, or the phone's own speech recognizer for a first draft), keeping the rule extractor on device too (it is pure Python and tiny; port it to Dart/Kotlin or run it on the server).
