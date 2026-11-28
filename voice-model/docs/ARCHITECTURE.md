# Architecture

## Data flow

```
                 ┌──────────────┐
  audio file ───►│   asr.py     │  faster_whisper | openai_api | mock
  (wav/mp3/m4a)  │ validate +   │  (auto = first one that works, mock always works)
                 │ transcribe   │
                 └──────┬───────┘
                        │ transcript (text)            typed text ──┐
                        ▼                                           │
                 ┌──────────────┐◄──────────────────────────────────┘
                 │ pipeline.py  │  process_text / process_audio, timings per stage
                 └──────┬───────┘
                        ▼
                 ┌──────────────┐   rules | llm | hybrid (default)
                 │ extractor.py │──────────────────────────────┐
                 └──────┬───────┘                              │ only if a field is
                        ▼                                      │ missing / low-confidence
        ┌───────────────────────────────┐                      ▼
        │ rule_extractor.py             │             ┌──────────────────┐
        │  normalize.py  (text cleanup) │             │ llm_extractor.py │ anthropic |
        │  currency.py   (EGP, USD...)  │             │ strict JSON +    │ openai_compatible
        │  rules: payment method        │             │ pydantic check,  │ (or Ollama)
        │  dates.py      (امبارح, 5/11) │             │ 1 retry, timeout,│
        │  merchants.py  (gazetteer)    │             │ disk cache       │
        │  numbers.py    (amount)       │             └────────┬─────────┘
        │  categories.py (keywords)     │                      │
        └───────────────┬───────────────┘                      │
                        ▼                                      ▼
                 field-by-field merge (field_sources) ◄────────┘
                        ▼
                 ExpenseDraft (schemas.py): values + confidence + needs_review + warnings + timings
                        ▼
        CLI (cli.py) · REST API (api.py) · Gradio demo (gradio_app.py)
                        ▼   user reviews / edits
                 POST /v1/expenses/confirm ──► storage.py (SQLite: transactions + corrections)
```

## Job of each module

| module | job | why it exists |
|---|---|---|
| `config.py` | settings from `.env` with safe defaults, Cairo timezone helper | one place to change behaviour; never crashes on missing keys |
| `schemas.py` | pydantic models: `ExpenseDraft`, `ConfirmRequest`, `ConfirmedTransaction` | the JSON contract with the mobile app, auto-documented in Swagger |
| `normalize.py` | digits → 0-9, remove diacritics, unify alef, split glued tokens, tokenize, language detection | one canonical spelling, so dictionaries stay small |
| `fuzzy.py` | string similarity (rapidfuzz, or identical pure-Python formula) | typo-tolerant merchant matching without a hard dependency |
| `numbers.py` | digits, English/Arabic number words, fractions, choosing the money amount | amounts are said in many ways and sentences have other numbers |
| `currency.py` | currency words → ISO code + token spans | strongest clue for which number is money |
| `dates.py` | relative/absolute dates and times with explicit `now` | deterministic tests; Egyptian conventions (d/m, weekdays) |
| `merchants.py` | gazetteer (89 merchants, 3 scripts), ambiguity rules, fuzzy, pattern | canonical names for reports and budgets |
| `categories.py` | keyword classifier with documented precedence | explicit words beat merchant defaults |
| `rule_extractor.py` | runs the modules in order, builds confidence + review flags | the free, offline, deterministic baseline |
| `llm_extractor.py` | optional LLM with JSON validation, retry, timeout, cache | understands free speech the rules miss |
| `extractor.py` | chooses rules / llm / hybrid and merges | uses the LLM only when it helps |
| `asr.py` | ASR backends behind one function, validation, hallucination filter | swap models without touching the rest |
| `pipeline.py` | `process_text`, `process_audio` with timings | every interface calls the same code |
| `storage.py` | SQLite save/list, correction statistics | "how often users correct a field" from real use |
| `api.py`, `cli.py`, `gradio_app.py` | interfaces | mobile app, teammates, live demo |

## Order inside the rule extractor (and why)

1. **currency** first — its token positions tell `numbers.py` which number is money.
2. **payment method** — so "فودافون كاش" is not taken as the merchant Vodafone, and "كارت شحن" (top-up card) is not taken as paying by card.
3. **date/time** — so "5" in "5 نوفمبر" or "3" in "الساعة 3" is never the amount.
4. **merchant (gazetteer)** — so digits inside names ("19011", "Route 66") are not amounts.
5. **amount** — scores all remaining numbers.
6. **merchant pattern/fuzzy** — only if the gazetteer found nothing.
7. **category**, **transaction type**, **note** (left-over words).

## Fallback matrix

| situation | what happens | where |
|---|---|---|
| no `faster-whisper` installed | `auto` tries openai_api (if key) → **mock**; message says why | `asr.backend_chain` |
| Whisper model cannot download (no internet) | that backend fails at runtime → next backend; warning in the draft | `asr.transcribe` |
| no GPU | device `cpu`, compute type `int8` | `FasterWhisperBackend._load` |
| explicit backend unavailable (e.g. `openai_api` without key) | falls back to mock with a warning | `asr.backend_chain` |
| mock backend without sidecar `.txt` | empty transcript + warning → draft with every field in `needs_review` | `MockBackend`, `pipeline` |
| empty / missing / too long / wrong format file | clear `AudioValidationError` → API 400/413/415 JSON, CLI message | `asr.validate_audio` |
| Whisper "hallucination" on silence (e.g. "ترجمة نانسي قنقر") | phrase removed, warning added | `asr._clean_hallucinations` |
| `LLM_PROVIDER=none` (default) | hybrid returns `hybrid:rules` | `extractor.extract` |
| LLM package or API key missing | warning "LLM unavailable (...), used rules" | `llm_extractor.make_client` |
| LLM timeout / exception | warning "LLM failed (...), used rules" | `LLMExtractor.extract` |
| LLM returns invalid JSON / bad values | one retry with the error message, then rules + warning | `LLMExtractor.extract` |
| no microphone (record_audio.py) | prints phone-recording instructions, `--scan` builds the manifest | `eval/record_audio.py` |
| no TTS engine (generate_audio.py) | prints install commands, exit code 0 | `eval/generate_audio.py` |
| no `tzdata` on Windows | fixed UTC+02:00 with a warning | `config.get_timezone` |
| no `rapidfuzz` / `jiwer` | pure-Python versions of the same formulas | `fuzzy.py`, `eval/metrics.py` |
| no `gradio` | clear install message | `gradio_app.build_demo` |
