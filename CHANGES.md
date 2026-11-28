# Changes

## 1.1.0

**Complete backend that saves transactions in PostgreSQL**
- New `backend/` Spring Boot 4 project (replaces the copy-paste snippets in `integration/`):
  `/api/voice-expenses/confirm` now saves the confirmed transaction in PostgreSQL; new
  `/api/transactions` endpoints to list, filter, add, edit and delete, and a monthly summary;
  `/api/health`; one error format for everything; Maven wrapper (no Maven install needed); 10 tests.
- Test page at http://localhost:8080/ : record with the laptop microphone or type, review, save,
  see the month's transactions and totals, delete.
- `api-tests.http` (VS Code REST Client) and `.vscode/` tasks to set up, start and test everything.

**Clean-up**
- Folder layout: `voice-service/` (Python) and `backend/` (Spring Boot); top-level README for running on a laptop.
- Removed `integration/` and `docs/MOBILE_INTEGRATION.md` (replaced by `backend/` and the README).
- Removed the `openai_whisper` speech-to-text backend: it needed torch and a system ffmpeg install,
  and faster-whisper (the default) runs the same Whisper models without either.
- Removed unused code (`merchant_names()`, `MerchantMatch.in_gazetteer`).
- Setup scripts now also install Whisper (`requirements-asr.txt`), so a fresh setup can transcribe.
- The mobile app is not part of this version; the API it will use is the backend API in the README.

## 1.0.1

- **Claude LLM mode works again.** `llm_extractor.py` no longer sends `temperature=0`: the default
  model `claude-haiku-5-5` rejects non-default sampling values with HTTP 400, so every LLM call
  failed and silently fell back to the rules. `max_tokens` raised from 500 to 4096 because the model
  thinks before answering and 500 could cut the JSON off. (The OpenAI-compatible/Ollama path is unchanged.)
- **`GET /` on the Python service** now redirects to `/docs` instead of returning `not_found`.
- **Spring Boot:** new `VoiceUploadLimitAdvice.java`. Recordings over 10 MB used to get an empty
  413 response (Spring rejects them before the controller runs); now they get the usual
  `{"error_code": "file_too_large", "message": ...}` JSON.
- **React Native `VoiceExpenseScreen.tsx`:**
  - corrected amounts are sent as typed. `Number("1,500")` and `Number("١٥٠٠")` are `NaN`, which was
    sent as `null` and failed with "amount required"; the server understands both strings;
  - type, category and payment method are tap-to-choose chips instead of free text (a category typo
    was saved as "other" without telling the user; an unknown payment method was rejected);
  - when nothing was heard, the server's `warnings` are shown (for example "Whisper not installed");
  - microphone/recording errors show an alert instead of an unhandled promise rejection.
- Tests for the root redirect and for the Claude request parameters.
