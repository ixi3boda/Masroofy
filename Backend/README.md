# Masroofy Backend

Spring Boot 3.5 (Java 17) API for the Masroofy mobile app (React Native). This module covers **authentication and authorization**
(screens 01-01 to 01-08).

- **Firebase Authentication** stores the credentials (password hashing, sign-in, ID and refresh tokens).
- **PostgreSQL**, accessed with **JdbcTemplate**, stores the `users` profile and the one-time `auth_codes`.
- **Flyway** creates the schema (`src/main/resources/db/migration`).

## Project layout

```
src/main/java/com/masroofy/backend
├── config/       Firebase, Security, CORS, Clock, typed @ConfigurationProperties
├── controller/   AuthController, UserController (REST endpoints only)
├── dto/
│   ├── request/  Validated request bodies
│   └── response/ Response bodies sent to the app
├── service/      AuthService, AuthCodeService, PasswordPolicy, EmailService (+ SMTP / log implementations)
├── repository/   JdbcTemplate repositories (UserRepository, AuthCodeRepository)
├── model/        Entities (User, AuthCode, AuthCodePurpose)
├── exception/    ErrorCode, ApiException, ErrorResponse, GlobalExceptionHandler
├── security/     FirebaseTokenFilter, AuthenticatedUser, ErrorResponseWriter
├── firebase/     FirebaseIdentityClient (Admin SDK + Auth REST API)
└── util/         EmailUtils (normalise and mask), SecureCodes (codes, tokens, HMAC)
```

## Running with Docker (recommended)

Everything Docker-related lives in this `Backend/` folder. Run these commands from `Backend/`.

**New team member?** Follow the step-by-step guide at the top of [`.env.example`](.env.example). In short:

1. `cp .env.example .env` (`.env` is git-ignored, so everyone makes their own).
2. Get access to the team's Firebase project, then put the service-account key at
   `Backend/secrets/firebase-service-account.json` and the Web API key in `FIREBASE_WEB_API_KEY`.
3. Fill in `DB_PASSWORD` (anything) and `AUTH_CODE_SECRET` (`openssl rand -hex 32`).
   Keep `MAIL_PROVIDER=log` to read codes from `docker compose logs backend` instead of email.
4. Start everything:

```bash
docker compose up -d --build
```

- API: http://localhost:8080 (port is `BACKEND_PORT`)
- **Swagger UI: http://localhost:8080/swagger-ui.html**. Click **Authorize** and paste the `accessToken` from login.
- **Frontend API docs:** [../docs/frontend-api/](../docs/frontend-api/00-instructions-for-claude.md), instructions plus one file per API.
- OpenAPI JSON: http://localhost:8080/v3/api-docs
- PostgreSQL: `localhost:5432` (port is `DB_PORT`); data persists in the `db-data` volume.

| File | Purpose |
|---|---|
| `Backend/Dockerfile` | Multi-stage: Maven build, then a JRE runtime as a non-root user. amd64 and arm64. |
| `../Database/Dockerfile` | PostgreSQL 16, UTC. Flyway in the backend creates the tables. |
| `docker-compose.yml` | Runs both services (builds `.` and `../Database`). Every setting comes from `.env`; the Firebase key is a compose secret. |
| `.env.example` | Every variable, documented. |
| `scripts/smoke-test.sh` | End-to-end check of every endpoint against the running stack (needs `MAIL_PROVIDER=log`). |

## Running without Docker

```bash
export FIREBASE_CREDENTIALS_PATH=/path/to/service-account.json   # or FIREBASE_CREDENTIALS_BASE64=<base64 of the JSON>
export FIREBASE_WEB_API_KEY=your-web-api-key AUTH_CODE_SECRET=$(openssl rand -hex 32)
export DB_URL=jdbc:postgresql://localhost:5432/masroofy DB_USERNAME=masroofy DB_PASSWORD=masroofy
SPRING_PROFILES_ACTIVE=dev ./mvnw spring-boot:run
```

With the `dev` profile (or `MAIL_PROVIDER=log`), emails are not sent. The codes are printed to the log instead.

### Environment variables

| Variable | Required | Purpose |
|---|---|---|
| `FIREBASE_CREDENTIALS_PATH` / `FIREBASE_CREDENTIALS_BASE64` | one of them (or Application Default Credentials) | Service-account JSON |
| `FIREBASE_WEB_API_KEY` | yes | Firebase REST sign-in and token refresh |
| `FIREBASE_PROJECT_ID` | no | Overrides the project ID in the credentials |
| `DB_URL`, `DB_USERNAME`, `DB_PASSWORD` | yes | PostgreSQL |
| `AUTH_CODE_SECRET` | yes (32+ chars) | HMAC key for stored codes and tokens |
| `MAIL_PROVIDER` | no (`smtp`) | `smtp`, or `log` for development |
| `MAIL_HOST`, `MAIL_PORT`, `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM` | when `smtp` | SMTP server. Gmail: `smtp.gmail.com`, `587`, your address, and an [App Password](https://myaccount.google.com/apppasswords). `MAIL_FROM` empty = send as `MAIL_USERNAME`. The app refuses to start if `smtp` is chosen without credentials. |
| `CORS_ALLOWED_ORIGINS` | no | Comma-separated browser origins. Native apps do not need this; Expo web in development needs `http://localhost:8081`. |
| `SWAGGER_ENABLED` | no (`true`) | Set `false` to hide Swagger UI and `/v3/api-docs` |

## Tests

```bash
./mvnw test
```

Docker must be running. Database tests (repositories and the full sign-up → reset flow) run against a real
**PostgreSQL 16 started by Testcontainers**. Firebase and SMTP are mocked in tests; the live check against real
Firebase is `scripts/smoke-test.sh`.

## API (v1)

The base path is `/api/v1`. All bodies are JSON and all timestamps are ISO-8601 UTC.
Protected endpoints need the header `Authorization: Bearer <accessToken>`.

| Screen | Method & path | Auth | Success |
|---|---|---|---|
| 01-02 Create an account | `POST /auth/register` | – | `201` `RegisterResponse` |
| 01-03 Verify signup email | `POST /auth/email-verification/verify` | – | `200` `{email, emailVerified}` |
| 01-03 Resend code | `POST /auth/email-verification/resend` | – | `202` `CodeDispatchResponse` |
| 01-04 Log in | `POST /auth/login` | – | `200` `AuthTokensResponse` |
| (silent) | `POST /auth/token/refresh` | – | `200` `AuthTokensResponse` |
| Log out | `POST /auth/logout` | Bearer | `204` |
| 01-05 Forgot password / 01-06 Resend | `POST /auth/password/forgot` | – | `202` `CodeDispatchResponse` |
| 01-06 Check your email | `POST /auth/password/verify-code` | – | `200` `{resetToken, expiresInSeconds}` |
| 01-07 Set new password → 01-08 | `POST /auth/password/reset` | – | `200` `{message}` |
| Home header / profile | `GET /users/me` | Bearer | `200` `UserResponse` |

### Request bodies

```jsonc
// POST /auth/register
{ "fullName": "Mariam Ali", "email": "mariam@example.com", "password": "Sunny-Nile9", "acceptedTerms": true }
// POST /auth/login
{ "email": "mariam@example.com", "password": "Sunny-Nile9" }
// POST /auth/email-verification/verify  and  POST /auth/password/verify-code
{ "email": "mariam@example.com", "code": "042517" }
// POST /auth/email-verification/resend  and  POST /auth/password/forgot
{ "email": "mariam@example.com" }
// POST /auth/password/reset
{ "resetToken": "<from verify-code>", "newPassword": "Fresh-Start7", "confirmPassword": "Fresh-Start7" }
// POST /auth/token/refresh
{ "refreshToken": "<from login>" }
```

### Response bodies

```jsonc
// UserResponse
{ "id": "uuid", "fullName": "Mariam Ali", "email": "mariam@example.com", "baseCurrency": "EGP",
  "locale": "en", "timezone": "Africa/Cairo", "emailVerified": true,
  "emailVerifiedAt": "2026-11-19T10:05:00Z", "createdAt": "2026-11-19T10:00:00Z" }   // phone omitted when null

// CodeDispatchResponse: show maskedEmail, draw codeLength boxes, disable "Resend" for resendAvailableInSeconds
{ "maskedEmail": "m***@example.com", "codeLength": 6, "expiresInSeconds": 600, "resendAvailableInSeconds": 60 }

// RegisterResponse
{ "user": { ...UserResponse }, "verification": { ...CodeDispatchResponse }, "verificationEmailSent": true }

// AuthTokensResponse: refresh before expiresIn (seconds) runs out
{ "accessToken": "...", "refreshToken": "...", "tokenType": "Bearer", "expiresIn": 3600, "user": { ...UserResponse } }
```

### Errors

Every error has the same shape. The app should switch on `code`, not on `message`.

```json
{
  "timestamp": "2026-11-19T10:00:00Z",
  "status": 400,
  "code": "WEAK_PASSWORD",
  "message": "The password does not meet the requirements.",
  "path": "/api/v1/auth/register",
  "fieldErrors": [ { "field": "password", "code": "NUMBER_OR_SYMBOL", "message": "Include a number or symbol" } ],
  "details": { "failedRules": ["NUMBER_OR_SYMBOL"] }
}
```

| Code | HTTP | When | Extra |
|---|---|---|---|
| `VALIDATION_FAILED` | 400 | Missing or invalid field, or terms not accepted | `fieldErrors` |
| `MALFORMED_REQUEST` | 400 | Body is not valid JSON | |
| `WEAK_PASSWORD` | 400 | Breaks 01-07 rules: `MIN_LENGTH`, `NUMBER_OR_SYMBOL`, `NO_PERSONAL_INFO`, `MAX_LENGTH`, `COMMON_PASSWORD` | `fieldErrors[].code` |
| `PASSWORDS_DO_NOT_MATCH` | 400 | `newPassword` ≠ `confirmPassword` | |
| `PASSWORD_REUSED` | 400 | The new password equals the current one | |
| `INVALID_CODE` | 400 | Wrong code | `details.remainingAttempts` |
| `INVALID_OR_EXPIRED_CODE` | 400 | No valid code. Ask for a new one. | |
| `INVALID_RESET_TOKEN` | 400 | Reset session expired or already used. Restart at 01-05. | |
| `INVALID_CREDENTIALS` | 401 | Wrong email or password | |
| `INVALID_REFRESH_TOKEN` | 401 | Refresh failed. Send the user to log in. | |
| `UNAUTHORIZED` | 401 | Missing, invalid, expired or revoked access token | |
| `EMAIL_NOT_VERIFIED` | 403 | Login or API call before verifying. Go to 01-03. | `details.maskedEmail` |
| `ACCOUNT_DISABLED` | 403 | Disabled in Firebase | |
| `EMAIL_ALREADY_IN_USE` | 409 | Sign-up with an existing email | |
| `EMAIL_ALREADY_VERIFIED` | 409 | Verify called again. Go to log in. | |
| `TOO_MANY_ATTEMPTS` | 429 | 5 wrong codes. The code is burned. | |
| `RESEND_COOLDOWN` | 429 | Asked for a new code within 60 s | `details.retryAfterSeconds`, `Retry-After` header |
| `RATE_LIMITED` | 429 | Firebase throttled sign-in | |
| `EMAIL_DELIVERY_FAILED` | 503 | SMTP failure | |
| `AUTH_PROVIDER_UNAVAILABLE` | 503 | Firebase unreachable or misconfigured | |
| `SERVICE_UNAVAILABLE` | 503 | Database unreachable (fails after 5 s) | |

### Security notes

- Passwords never touch the database. Codes and reset tokens are stored only as HMAC-SHA256 hashes.
  Each code is single-use, expires after 10 minutes and allows 5 attempts. Asking for a new code cancels the old one.
- Forgot password and resend give the same answer for unknown emails, so they do not reveal which emails have accounts.
  The 60 s cooldown is kept per email address (table `code_dispatches`, keyed by an HMAC of the email) and checked
  before the account lookup, so the second call answers `429` for unknown emails too.
- Concurrency: code checks and code issuing lock the user's row, so parallel guesses still count toward the
  5 attempts and parallel resends get one code. Sign-up takes a PostgreSQL advisory lock per email, so parallel
  sign-ups create one Firebase account; a failed sign-up's Firebase account is deleted with retries.
- Resetting the password signs the user out everywhere, and so does logout. Both raise the user's `session_version`
  (DB column and Firebase custom claim) and revoke Firebase refresh tokens. Access tokens and refresh tokens issued
  before that are rejected immediately, even one issued a moment earlier. Firebase's own check
  (`app.firebase.check-revoked`) works in whole seconds and misses those.
- `refreshToken` is opaque: the backend wraps Firebase's token as `<sessionVersion>.<HMAC>.<token>`.
- Users whose email is not verified are authenticated but cannot reach any data endpoint.
