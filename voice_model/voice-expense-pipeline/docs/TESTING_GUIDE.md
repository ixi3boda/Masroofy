# Testing guide (step by step)

You do not need to know ML to follow this. Run each step in a terminal opened in the project folder.
Windows: use `py` instead of `python3` if `python` is not found, and `.venv\Scripts\activate` instead of `source .venv/bin/activate`.

## Step 1 — install (once)
```bash
python -m venv .venv
source .venv/bin/activate            # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```
✅ You should see "Successfully installed ...". (Or just run `bash setup.sh` / `setup.bat`.)

## Step 2 — smoke test (10 seconds, offline)
```bash
python scripts/smoke_test.py
```
✅ 8 lines starting with `[PASS]` and `SMOKE TEST PASSED ✅`.
❌ If a line says FAIL, read the "expected … got …" text. `fastapi/httpx not installed` means step 1 did not finish.

## Step 3 — unit tests
```bash
pytest -q
```
✅ Something like `268 passed` (a few tests may be "skipped" if optional packages are missing — that is fine).

## Step 4 — try your own sentences
```bash
python -m voice_expense.cli text "صرفت 250 على groceries امبارح" --now 2026-11-20T14:00
python -m voice_expense.cli text "I paid 80 pounds for coffee at Cilantro this morning"
python -m voice_expense.cli interactive
```
In `interactive`: type a sentence, check the draft, type `amount=200` to correct a field, press Enter to save. `python -m voice_expense.cli list` shows saved items.

**If something is extracted wrongly, write it down** (sentence + what you expected) and add it to `eval/dataset/phrases.jsonl` — that is how the dataset grows.

## Step 5 — text evaluation (extraction only)
```bash
python eval/evaluate.py --mode text --extractor rules
python eval/evaluate.py --mode text --dataset eval/dataset/challenge_unseen.jsonl
python eval/evaluate.py --mode text --compare          # rules vs hybrid (hybrid needs an LLM configured)
```
✅ `Report written to results/<time>/report.md`. Open it: per-field accuracy by language, correction rate, latency. `errors.csv` lists only the mistakes.

What the scores mean (all in %, in report.md and printed in the terminal):

| metric | question it answers |
|---|---|
| accuracy | of all examples, how often was this field exactly right (including "correctly empty")? |
| precision | when the system filled the field, how often was it right? (low = it invents/guesses wrong values) |
| recall | of the fields that should have a value, how many did it get right? (low = it misses things) |
| F1 | one number balancing precision and recall (harmonic mean) |
| micro | all fields pooled together |
| macro / weighted F1 (category) | average over categories: macro treats every category equally, weighted by how many examples each has |
| confusion_category.csv | which category was confused with which (rows = correct, columns = predicted) |
| needs_review precision / recall / F1 | does the ⚠️ highlight point at the fields that are really wrong? |

A wrong value counts as both a false positive and a false negative (standard for information extraction). For `payment_method`, "unknown" counts as empty.

## Step 6 — real speech-to-text
```bash
pip install -r requirements-asr.txt
python -m voice_expense.cli audio path/to/recording.m4a --now 2026-11-20T14:00
```
The first run downloads the Whisper model (`small` ≈ 480 MB) — needs internet once. On a laptop CPU expect a few seconds per short clip with `small`. Set `WHISPER_MODEL=base` in `.env` for faster (less accurate) tests.

## Step 7 — audio evaluation
Synthetic voices (quick, optimistic):
```bash
pip install -r requirements-audio-gen.txt
python eval/generate_audio.py --limit 20
python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv
python eval/evaluate.py --mode audio --manifest eval/audio/synthetic/manifest.csv --compare   # Arabic forced vs auto language
```
Real voices (the honest numbers — every teammate should do this):
```bash
python eval/record_audio.py --speaker yourname          # Enter to start, Enter to stop
python eval/evaluate.py --mode audio --manifest eval/audio/real/manifest.csv
```
No microphone? Record on your phone, name files by id (`ar_01.m4a`), copy them to `eval/audio/real/yourname/`, then `python eval/record_audio.py --speaker yourname --scan`.

## Step 7b — accuracy on what users confirmed (real usage)
Every Confirm (Gradio demo, CLI `interactive`, or `POST /v1/expenses/confirm`) stores the original draft AND the
final values. This script treats the confirmed values as the correct answer:
```bash
python eval/confirmed_report.py                    # reads expenses.db
python eval/confirmed_report.py --since 2026-11-24 # only recent ones
```
✅ `results/confirmed-<time>/report.md` with accuracy, precision/recall/F1, correction rate (voice vs typed, per
language), ⚠️-highlight quality and latency, plus `transactions.csv` (draft vs confirmed for every field).
Rule for testers: **always fix every wrong field before pressing Confirm** — a field you leave unchanged counts as correct.

## Step 8 — API
```bash
uvicorn voice_expense.api:app --reload
```
Open http://127.0.0.1:8000/docs → `POST /v1/expenses/parse-text` → "Try it out" → Execute. See docs/API.md.

## Step 9 — web demo with microphone
```bash
pip install -r requirements-demo.txt
python -m voice_expense.gradio_app
```
Open the printed URL (http://127.0.0.1:7860), allow microphone access, record, Parse, edit, Confirm.

## Troubleshooting
| problem | fix |
|---|---|
| Arabic shows as `???` or boxes on Windows | run `chcp 65001` first, use Windows Terminal; the scripts already switch output to UTF-8 |
| `ZoneInfoNotFoundError` / timezone warning | `pip install tzdata` (it is in requirements.txt) |
| `ModuleNotFoundError: voice_expense` | run commands from the project folder (the one with README.md) |
| Whisper model download fails | needs internet the first time; or set `ASR_BACKEND=mock` to test without a model |
| `Could not load library cudnn...` on GPU | set `WHISPER_DEVICE=cpu`, or in Colab use the GPU runtime as described in COLAB.md |
| faster-whisper cannot open .m4a/.webm | it decodes with PyAV (bundled). If a file still fails, convert it: `ffmpeg -i in.m4a -ar 16000 -ac 1 out.wav` |
| very slow transcription | use `WHISPER_MODEL=base` or `small`, keep clips short, or use a GPU |
| port 8000 already in use | `uvicorn voice_expense.api:app --port 8001` |
| LLM "unavailable" warning | expected when `LLM_PROVIDER=none`; to enable see README → Optional LLM |
| microphone does not work in the browser | use http://127.0.0.1 (browsers block the mic on other http addresses), or the `--share` https link |
