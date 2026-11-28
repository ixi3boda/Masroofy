# Masroofy voice expenses

Say or type an expense in Egyptian Arabic, English or both ("دفعت 150 جنيه في Uber امبارح"), check the
draft, and save it as a transaction in **PostgreSQL**.

```
 browser test page / mobile app          backend (Spring Boot, port 8080)          voice-service (Python, port 8000)
 ─────────────────────────────          ───────────────────────────────          ─────────────────────────────────
 record or type an expense  ──────────► /api/voice-expenses/parse-*   ─────────► Whisper speech-to-text + field extraction
 review the draft, fix fields  ◄─────── returns a draft (nothing saved) ◄─────── returns the draft
 Confirm & save  ─────────────────────► /api/voice-expenses/confirm   ─────────► validates the corrections
                                        saves the transaction in PostgreSQL
 list / summary / edit / delete  ─────► /api/transactions
```

| folder | what it is |
|---|---|
| `backend/` | Spring Boot 4 + PostgreSQL. The only server the app talks to. Saves transactions. Also serves a **test page** at http://localhost:8080/ |
| `voice-service/` | Python (FastAPI + Whisper). Turns speech/text into a draft. Also has the accuracy evaluation tools (see `voice-service/README.md`) |
| `api-tests.http` | Every API request, ready to send from VS Code |
| `.vscode/` | Tasks to start/test everything, debug configurations, recommended extensions |

## What you need on the laptop

- **VS Code**, with the extensions it suggests when you open this folder (Java, Spring Boot, Python, REST Client)
- **Java 17 or newer** (a JDK, e.g. Temurin from adoptium.net). Maven is **not** needed: `backend/mvnw` downloads it
- **Python 3.10–3.13**
- **PostgreSQL** (with pgAdmin or psql)
- Internet the first time (Maven/Python packages and the Whisper model, about 500 MB in total)

No phone and no Android Studio needed.

## First time (once)

1. **Create the database.** In pgAdmin: right-click *Databases > Create > Database…*, name it `masroofy`. Or in a terminal:
   ```bash
   psql -U postgres -c "CREATE DATABASE masroofy;"
   ```
   The table is created automatically when the backend starts.

2. **Set your PostgreSQL password.** Open `backend/src/main/resources/application.properties` and change
   the default after `DB_PASSWORD:` on this line to your password:
   ```properties
   spring.datasource.password=${DB_PASSWORD:postgres}
   ```
   Change `DB_USERNAME` the same way if your user is not `postgres`.

3. **Open the folder in VS Code** (*File > Open Folder…* → this `voice-expense-pipeline` folder) and install the recommended extensions when asked.

4. **Set up the voice service:** *Terminal > Run Task… > Set up voice service (first time only)*.
   It creates `voice-service/.venv`, installs the packages (including Whisper) and ends with `SMOKE TEST PASSED`.

## Every time

*Terminal > Run Task… > **Start backend + voice service***. Two terminals open; wait for
`Uvicorn running on http://127.0.0.1:8000` and `Started MasroofyApplication`.

Then test in any of these ways:

| how | what to do |
|---|---|
| **Test page (easiest)** | Open **http://localhost:8080/** in Chrome or Edge. Press **Record**, say an expense, press **Stop** (or type a sentence and press *Parse text*). Check the fields, press **Confirm & save**, and it appears in the table below (read from PostgreSQL). The first recording takes longer because Whisper downloads/loads its model |
| **REST Client** | Open `api-tests.http` and click **Send Request** above any request |
| **Database** | In pgAdmin: *masroofy > Schemas > public > Tables > transactions > View/Edit Data* |
| **Automated tests** | *Terminal > Run Task… > Backend tests* (10 tests, uses an in-memory database, no PostgreSQL needed) and *Voice service tests* (290+ tests) |

To stop: click the trash icon on each task terminal (or Ctrl+C in it).

Without VS Code tasks, the same commands in two terminals:
```bash
cd voice-service && .venv/bin/python -m uvicorn voice_expense.api:app --host 127.0.0.1 --port 8000
```
```bash
cd backend && ./mvnw spring-boot:run
```
On Windows: `.\.venv\Scripts\python.exe -m uvicorn voice_expense.api:app --host 127.0.0.1 --port 8000` and `.\mvnw.cmd spring-boot:run`.

## Backend API

All JSON uses snake_case. Every error is `{"error_code": "...", "message": "..."}`.

| method | URL | what it does |
|---|---|---|
| GET | `/api/health` | database and voice service status |
| POST | `/api/voice-expenses/parse-text` | `{"text": "...", "reference_time"?: ISO time}` → draft (not saved) |
| POST | `/api/voice-expenses/parse-audio` | multipart `file` (.m4a .mp3 .wav .ogg .webm…, ≤ 10 MB, ≤ 60 s), `reference_time`? → draft |
| POST | `/api/voice-expenses/confirm` | `{"draft": <draft as received>, "corrections": {only changed fields}}` → **saves**, 201 + transaction |
| GET | `/api/transactions` | list, newest first; optional `from`, `to` (YYYY-MM-DD), `category`, `type`, `limit` (≤ 500) |
| GET | `/api/transactions/summary?month=2026-11` | totals per currency: spent, income, net, spending per category |
| GET | `/api/transactions/{id}` | one transaction |
| POST | `/api/transactions` | add without voice; only `amount` is required |
| PUT | `/api/transactions/{id}` | edit (a missing `date` keeps the saved date) |
| DELETE | `/api/transactions/{id}` | delete (204) |
| GET | `/api/transactions/categories` | the 18 category ids |

A saved transaction:
```json
{
  "id": 1, "transaction_type": "expense", "amount": 160.00, "currency": "EGP", "merchant": "Uber",
  "category": "transport", "date": "2026-11-26", "time": null, "payment_method": "card", "note": null,
  "source": "voice", "transcript": "دفعت 150 جنيه في Uber امبارح", "language": "mixed",
  "edited_fields": ["amount", "payment_method"], "extraction_method": "hybrid:rules",
  "voice_record_id": 1, "user_id": null, "created_at": "...", "updated_at": "..."
}
```
`source` is `voice` (recording), `text` (typed sentence) or `manual` (form). `edited_fields` are the
fields the user corrected before saving, which is the data for the "how often do users correct the model" metric.

**Users:** there is no login yet, so every transaction is shared (`user_id` is null). When you add
Spring Security, return the logged-in user's id from `backend/src/main/java/com/masroofy/common/CurrentUser.java`;
saving and listing already filter by it.

## Troubleshooting

| problem | fix |
|---|---|
| Backend stops with `password authentication failed` | wrong PostgreSQL password in `application.properties` (step 2) |
| `database "masroofy" does not exist` | step 1 |
| `Connection to localhost:5432 refused` | PostgreSQL is not running (Windows: *Services > postgresql-x64 > Start*) |
| `/api/health` says `voice_service: unavailable` | the Python task is not running |
| `{"error_code":"not_found"}` | wrong URL: `/api/...` is on port 8080 (backend), not 8000 |
| Port 8080 already in use | stop the other program, or set `server.port=8081` in `application.properties` |
| `JAVA_HOME` / `java` not found | install a JDK 17+ and restart VS Code |
| Record button: microphone blocked | use `http://localhost:8080` (not your IP) and allow the microphone |
| Every recording comes back empty | read the warnings under the form: usually Whisper could not download (needs internet once) |
| First recording very slow | normal: the Whisper model loads once, later ones are faster. On a slow laptop set `WHISPER_MODEL=base` in `voice-service/.env` |
| Arabic shows as `????` in the Windows terminal | `chcp 65001`, or use the test page |

## Sharing

`python make_zip.py` in this folder creates `voice-expense-pipeline.zip` without virtualenvs, build
output, databases or `.env` files.
