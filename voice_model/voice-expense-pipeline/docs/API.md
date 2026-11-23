# REST API

Start: `uvicorn voice_expense.api:app --reload` → Swagger UI with try-it-out at http://127.0.0.1:8000/docs

All times use Africa/Cairo. Send `reference_time` when you want relative words ("امبارح") resolved against a specific moment (tests, demos); otherwise the server's current time is used.

## GET /health
```json
{
  "status": "ok", "version": "1.0.0",
  "asr_backend": "faster_whisper", "asr_backend_setting": "auto", "asr_language": "ar",
  "extractor_mode": "hybrid", "llm_provider": "none", "llm_available": false,
  "llm_unavailable_reason": "LLM_PROVIDER=none", "timezone": "Africa/Cairo"
}
```

## POST /v1/expenses/parse-text
Request:
```json
{"text": "صرفت 250 على groceries امبارح", "reference_time": "2026-11-20T14:00:00+02:00", "extractor": "rules"}
```
`reference_time` and `extractor` (rules | llm | hybrid) are optional.

Response 200 (`ExpenseDraft`):
```json
{
  "transaction_type": "expense",
  "amount": 250.0,
  "currency": "EGP",
  "merchant": null,
  "category": "groceries",
  "date": "2026-11-19",
  "time": null,
  "payment_method": "unknown",
  "note": "groceries",
  "confidence": {"transaction_type": 0.9, "amount": 0.75, "currency": 0.7, "merchant": 0.6, "category": 0.85,
                 "date": 0.95, "time": 0.0, "payment_method": 0.6, "note": 0.6},
  "needs_review": [],
  "language": "mixed",
  "transcript": "صرفت 250 على groceries امبارح",
  "normalized_text": "صرفت 250 علي groceries امبارح",
  "extraction_method": "rules",
  "warnings": [],
  "timings_ms": {"asr": 0.0, "normalize": 0.1, "extract": 1.2, "total": 1.4, "model_load": 0.0},
  "reference_time": "2026-11-20T14:00:00+02:00",
  "category_candidates": [{"category": "groceries", "score": 1.0, "source": "keyword"}],
  "field_sources": {"amount": "rules", "category": "rules", "...": "rules"}
}
```
How the app should use it:
- Show every field in an editable form; **highlight the names in `needs_review`**.
- Show `transcript` so the user can see what was heard.
- `warnings` are for logs / a small info icon.
- `category_candidates` can feed a "did you mean" chip.

## POST /v1/expenses/parse-audio
`multipart/form-data` fields:

| field | required | example |
|---|---|---|
| `file` | yes | recording (.wav .mp3 .m4a .ogg .webm .flac .aac .opus), ≤ 10 MB, ≤ 60 s |
| `reference_time` | no | `2026-11-20T14:00:00+02:00` |
| `language` | no | `ar` \| `en` \| `auto` |
| `extractor` | no | `rules` \| `llm` \| `hybrid` |

```bash
curl -X POST http://127.0.0.1:8000/v1/expenses/parse-audio \
  -F "file=@my_expense.m4a" -F "reference_time=2026-11-20T14:00:00+02:00"
```
Response: same `ExpenseDraft` as above, with `timings_ms.asr` and `timings_ms.model_load` filled. The uploaded file is saved to a temporary file and always deleted afterwards.

## POST /v1/expenses/confirm
Send the draft exactly as received plus only the fields the user changed:
```json
{
  "draft": { "...the ExpenseDraft from parse-text/parse-audio...": "" },
  "corrections": {"amount": 160, "payment_method": "card"}
}
```
Allowed correction keys: `transaction_type, amount, currency, merchant, category, date, time, payment_method, note`.

Response 201 (`ConfirmedTransaction` = the final draft + storage info):
```json
{
  "id": 12, "created_at": "2026-11-20T14:03:11+02:00",
  "user_edited_fields": ["amount", "payment_method"],
  "amount": 160.0, "payment_method": "card", "currency": "EGP", "merchant": "Uber", "category": "transport",
  "date": "2026-11-20", "...": "all other ExpenseDraft fields"
}
```
`user_edited_fields` only lists fields whose value really changed. This feeds the correction-rate metric.

## GET /v1/expenses?limit=50
List of `ConfirmedTransaction`, newest first.

## GET /v1/expenses/stats
Correction rate from real usage:
```json
{"transactions": 40, "with_at_least_one_correction": 9, "pct_with_correction": 22.5,
 "avg_fields_corrected": 0.275, "per_field": {"amount": 3, "merchant": 5, "category": 3}}
```

## Errors
Every error has the same shape:
```json
{"error_code": "unsupported_audio_format", "message": "Unsupported audio format '.txt'. Use one of: ..."}
```

| HTTP | error_code | when |
|---|---|---|
| 400 | `empty_text` | text is only spaces |
| 400 | `empty_audio` | uploaded file is empty or has no audio |
| 400 | `audio_not_found` | (internal) temp file missing |
| 413 | `file_too_large` | upload larger than `MAX_UPLOAD_MB` |
| 413 | `audio_too_long` | recording longer than `ASR_MAX_DURATION_S` |
| 415 | `unsupported_audio_format` | extension not supported |
| 422 | `validation_error` | missing/invalid JSON fields (message lists them) |
| 422 | `invalid_reference_time`, `invalid_language`, `invalid_extractor`, `invalid_limit` | bad parameter |
| 422 | `amount_required` | confirm without an amount |
| 422 | `invalid_correction` | a corrected value is invalid (e.g. currency "XX") |
| 404 | `not_found` | unknown URL |
| 500 | `internal_error` | unexpected bug (please report with the message) |
