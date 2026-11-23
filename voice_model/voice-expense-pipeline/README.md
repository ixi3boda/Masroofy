# voice-expense-pipeline

Speak (or type) an expense in **Egyptian Arabic, English or a mix of both** and get a structured
**draft transaction** that the user reviews and confirms in the app.

```
"دفعت 150 جنيه في Uber امبارح"  →  {amount: 150.00, currency: EGP, merchant: Uber,
                                     category: transport, date: 2026-11-19, needs_review: []}
```

Graduation project — Personal Finance and Investment Mobile App, Computer and Communications Engineering,
Alexandria University, 2026–2027. This repository is the voice-entry feature: speech-to-text, field
extraction, the review/confirm flow, a REST API for the mobile app, a web demo and the evaluation tooling.

## Quick start (5 commands)

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: python -m venv .venv  then  .venv\Scripts\activate
pip install -r requirements.txt
python scripts/smoke_test.py                             # → all PASS (offline, no models)
pytest -q                                                # → all pass
python -m voice_expense.cli text "صرفت 250 على groceries امبارح" --now 2026-11-20T14:00
```
The last command prints amount 250, EGP, category groceries, date 2026-11-19.
(Or run `bash setup.sh` / `setup.bat`, which does the first three for you.)

## All commands

| # | command | what you get |
|---|---|---|
| 1 | `python -m venv .venv && source .venv/bin/activate` (Windows: `python -m venv .venv` then `.venv\Scripts\activate`) | isolated Python environment |
| 2 | `pip install -r requirements.txt` | core packages (no torch, no models) |
| 3 | `python scripts/smoke_test.py` | 8 PASS lines, offline |
| 4 | `pytest -q` | all tests pass |
| 5 | `python -m voice_expense.cli text "صرفت 250 على groceries امبارح" --now 2026-11-20T14:00` | draft JSON + bilingual summary |
| 6 | `python eval/evaluate.py --mode text --extractor rules` | `results/<time>/report.md` |
| 7 | `pip install -r requirements-asr.txt` then `python -m voice_expense.cli audio <file>` | real Whisper transcription + draft |
| 8 | `pip install -r requirements-audio-gen.txt && python eval/generate_audio.py --limit 20` then `python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv` | end-to-end audio evaluation (WER/CER, latency) |
| 9 | `uvicorn voice_expense.api:app --reload` → http://127.0.0.1:8000/docs | REST API with Swagger |
| 10 | `pip install -r requirements-demo.txt && python -m voice_expense.gradio_app` | microphone web demo (`--share` for a public link) |

Windows note: commands are the same except activation (`.venv\Scripts\activate`) and, if `python` is not found, use `py`.
If Arabic looks broken in the console, run `chcp 65001` or use Windows Terminal.

Google Colab (GPU, `large-v3`, public demo link): see **docs/COLAB.md**.

## What each part does

| part | files | in one sentence |
|---|---|---|
| Speech-to-text | `voice_expense/asr.py` | faster-whisper (CPU int8 / GPU float16) by default; openai-whisper, OpenAI API or a **mock** backend that reads `clip.txt` next to `clip.wav` so everything works without a model |
| Normalization | `normalize.py` | ١٥٠→150, أ/إ/آ→ا, removes diacritics, splits "150ج"/"بـ150", keeps Franco words like "dafa3t" intact |
| Field extraction (rules) | `numbers.py`, `currency.py`, `dates.py`, `merchants.py`, `categories.py`, `rule_extractor.py` | offline, deterministic, ~1 ms per sentence |
| Field extraction (LLM, optional) | `llm_extractor.py`, `extractor.py` | Claude or any OpenAI-compatible model (incl. free local **Ollama**) for hard sentences, validated JSON, falls back to rules on any problem |
| Draft → review → confirm | `schemas.py`, `storage.py` | per-field confidence + `needs_review`; only confirmed items go to SQLite, with the fields the user corrected |
| Interfaces | `cli.py`, `api.py`, `gradio_app.py` | terminal, REST API for the mobile app, browser demo with microphone |
| Evaluation | `eval/` | 100 labeled phrases (30 Arabic, 30 English, 30 mixed, 10 Franco) + 30 unseen ones, TTS audio generator, recorder, metrics + Markdown report |
| Tests | `tests/`, `scripts/smoke_test.py` | 260+ offline tests and a 10-second smoke test |

Data you can edit without code: `voice_expense/data/merchants.json` (89 merchants with Latin/Arabic/Franco
aliases) and `voice_expense/data/categories.json` (18 categories with keywords).

## Using it from Python

```python
from voice_expense import process_text, process_audio
d = process_text("اشتريت شاحن من B.Tech بألف وخمسمية جنيه", now="2026-11-20T14:00")
print(d.amount, d.merchant, d.category, d.needs_review)     # 1500.00 B.Tech electronics []
d = process_audio("my_expense.m4a")                         # uses ASR_BACKEND from .env
```

## Settings (.env)

Copy `.env.example` to `.env`. Everything has a safe default; the most useful settings:

| setting | default | meaning |
|---|---|---|
| `ASR_BACKEND` | `auto` | `auto`, `faster_whisper`, `openai_whisper`, `openai_api`, `mock` |
| `WHISPER_MODEL` | `small` | `base` (fast), `small` (CPU default), `medium`/`large-v3` (GPU) |
| `WHISPER_DEVICE` | `cpu` | `cpu` always works; `cuda`/`auto` only with NVIDIA CUDA 12 + cuDNN installed (e.g. Colab) |
| `ASR_LANGUAGE` | `ar` | forcing Arabic works better for Egyptian/mixed speech; `auto` to compare |
| `EXTRACTOR_MODE` | `hybrid` | `rules`, `llm`, `hybrid` (rules first, LLM only when unsure) |
| `LLM_PROVIDER` | `none` | `anthropic` or `openai_compatible` |

### Optional LLM

* **Claude**: `pip install -r requirements-llm.txt`, then in `.env`: `LLM_PROVIDER=anthropic`, `ANTHROPIC_API_KEY=...` (model defaults to `claude-haiku-5-5`, change with `LLM_MODEL`).
* **OpenAI**: `LLM_PROVIDER=openai_compatible`, `OPENAI_API_KEY=...`, `LLM_MODEL=gpt-4o-mini`.
* **Free and offline with Ollama**: install https://ollama.com, run `ollama pull qwen2.5:7b`, then
  `LLM_PROVIDER=openai_compatible`, `OPENAI_BASE_URL=http://localhost:11434/v1`, `OPENAI_API_KEY=ollama` (any text), `LLM_MODEL=qwen2.5:7b`.

Answers are cached in `.cache/llm/` so repeated evaluations are free (`LLM_CACHE=0` to disable).
If the key is missing, the package is missing, the call times out or the JSON is invalid, you get a
warning in the draft and the rule-based result — never a crash.

## Measured results (text mode, rules only)

Measured on 2026-11-23 (Python 3.13, 2-core CPU, no GPU). Reproduce with
`python eval/evaluate.py --mode text --extractor rules`.

| dataset | n | amount | merchant | category | date | full-record exact match | avg fields to fix | mean / p95 latency |
|---|---|---|---|---|---|---|---|---|
| `phrases.jsonl` (main) | 100 | 100% | 100% | 100% | 100% | 100% | 0.00 | 0.6 / 1.1 ms |
| `challenge_unseen.jsonl` | 30 | 100% | 93.3% | 96.7% | 100% | 90% | 0.10 | 0.8 / 1.6 ms |

**Read these numbers carefully.** The main dataset was written together with the rules, so 100% shows
that the rules cover the designed cases — it is an upper bound, not real-world accuracy. The 30
challenge phrases were written afterwards and never used for tuning; the misses there (an unknown
restaurant, a mall not in the gazetteer, "electricity card top-up") are the kind of errors to expect.
Audio numbers (WER/CER, end-to-end accuracy, Whisper latency) have not been measured yet: run
step 8 and record real voices (docs/TESTING_GUIDE.md). See docs/LIMITATIONS.md.

## Troubleshooting

| problem | fix |
|---|---|
| `ModuleNotFoundError` | activate the venv and run commands from this folder |
| smoke test says fastapi not installed | `pip install -r requirements.txt` did not finish — rerun it |
| Arabic printed as `????` (Windows) | `chcp 65001`, or Windows Terminal |
| timezone warning on Windows | `pip install tzdata` |
| Whisper download fails | needs internet once; meanwhile use `ASR_BACKEND=mock` |
| faster-whisper cannot read a file | it decodes wav/mp3/m4a/ogg/webm itself (PyAV) and normally needs **no system ffmpeg**; if one file still fails, convert it: `ffmpeg -i in.m4a -ar 16000 -ac 1 out.wav` |
| openai-whisper errors about ffmpeg | that backend needs system ffmpeg (`apt install ffmpeg` / `brew install ffmpeg` / `winget install ffmpeg`) |
| CUDA / cuDNN error | `WHISPER_DEVICE=cpu` |
| slow on CPU | `WHISPER_MODEL=base`, shorter clips, or Colab GPU |
| microphone blocked in browser | open http://127.0.0.1:7860 (not a LAN IP) or use `--share` |

More: docs/TESTING_GUIDE.md · docs/ARCHITECTURE.md · docs/API.md · docs/DECISIONS.md · docs/LIMITATIONS.md

## Share with the team

```bash
python make_zip.py      # → voice-expense-pipeline.zip (no .venv, .env, databases, results or audio)
```
