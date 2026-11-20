# SMS transaction capture — React Native + Spring Boot + PostgreSQL

Captures incoming bank and wallet SMS on Android. When a message is a transaction (purchase, ATM withdrawal,
transfer, salary, bill, refund…), it updates the matching account with the **date and time, amount, type and
the bank or app** that made it. Unclear cases wait for the user's review, as the proposal requires
("suggests details for review", "repeated … uploads should trigger review rather than silently add duplicates").

```
 Android phone                                         Spring Boot                           PostgreSQL
 ─────────────                                         ───────────                           ──────────
 SMS arrives ─► SmsReceiver                            POST /api/sms/ingest
                 ├─ sender on bank/wallet list? no ─► ignored, never read further
                 ├─ OTP code? yes ─► dropped on phone (never uploaded)
                 └─ SmsUploadWorker (queued, retries   ─► SmsIngestService
                    offline, survives reboot)              ├─ already received? ─► stop
                                                           ├─ SmsParser (trained model, Java)
                                                           │    not a transaction ─► store hash only
                                                           ├─ bank/app from sender ID
                                                           ├─ match account (bank + last 4 digits)
                                                           ├─ date/time (Cairo), duplicate check,
                                                           │  own-account transfer link
                                                           ├─ clear? ─► lock account row, update   ─► accounts.balance
                                                           │            balance (CONFIRMED)          transactions
                                                           └─ unclear ─► DRAFT + reasons            sms_messages
 React Native: SmsReviewScreen ◄──── GET /api/sms/review, POST …/confirm, …/reject
```

## What's in here
| Folder | Contents |
|---|---|
| `backend/` | Spring Boot package `com.financeapp.sms`: parser, entities, repositories, services, REST controller, Flyway SQL, model file, tests |
| `android/` | Java classes for your RN app's `android/app/src/main/java/<your package>/sms/`, manifest and Gradle additions |
| `react-native/src/sms/` | `smsCapture.ts` (native wrapper + permission), `smsApi.ts` (backend calls), `SmsReviewScreen.tsx`, `SmsPasteScreen.tsx` |
| `model/` | Python training/evaluation (`sms_model.py`, `evaluate.py`), exporter for Java, dataset, trained model |

Rename the package `com.financeapp` to your app's package in both `backend/` and `android/`.

## Backend setup (Spring Boot 3, Java 17+)
1. Copy `backend/src/main/java/com/financeapp/sms/**` and `backend/src/main/resources/{sms,db}/**` into your project.
2. Dependencies (most you already have): `spring-boot-starter-web`, `spring-boot-starter-data-jpa`,
   `spring-boot-starter-security`, `org.postgresql:postgresql`, `org.flywaydb:flyway-core` and
   `org.flywaydb:flyway-database-postgresql`. The parser itself needs nothing extra.
3. **Adapt `security/CurrentUser.java`** to how your JWT exposes the user id (it assumes the authentication
   name is the numeric id). Every query is filtered by this id, so users only see their own records.
4. **Existing tables:** if you already have `accounts`/`transactions`, merge the columns instead of using the
   two `CREATE TABLE`s in `V100__sms_capture.sql` (the `ALTER` statements are at the bottom of that file), and map
   the fields onto your entities. Money is `NUMERIC(14,2)` / `BigDecimal`.
5. Optional settings: `application-sms-example.yml` (auto-confirm on/off, confidence threshold, windows, senders).

**Senders = "the bank or app".** Each SMS sender ID (e.g. `NileBank`) maps to an institution name stored on the
transaction. The built-in list holds the dataset's 8 fictional senders: replace it with your real banks' sender IDs.
Users can add or rename one: `PUT /api/sms/senders {"senderId":"VF-Cash","institution":"Vodafone Cash","kind":"WALLET"}`.

### API
| Method | Path | Purpose |
|---|---|---|
| POST | `/api/sms/ingest` | `{"messages":[{"sender","body","receivedAt"(epoch ms)}]}` → one result per SMS: `APPLIED`, `DRAFT`, `IGNORED`, `ALREADY_RECEIVED` |
| GET | `/api/sms/senders` | Bank/wallet sender IDs; the phone's allow-list |
| PUT | `/api/sms/senders` | Add, rename or disable a sender |
| GET | `/api/sms/review` | Drafts waiting for review |
| POST | `/api/sms/transactions/{id}/confirm` | Confirm, optionally with `accountId`, `type`, `amount`, `fee`, `merchant`, `occurredAt`, `category`. Also corrects confirmed ones |
| POST | `/api/sms/transactions/{id}/reject` | Reject; gives the money back to the balance if it had been applied |

**Review reasons:** `NO_ACCOUNT` (first SMS from a bank/card: the user picks the account once, and the app remembers the
bank name and last 4 digits), `UNKNOWN_SENDER`, `LOW_CONFIDENCE` (model < 0.85), `FOREIGN_CURRENCY` (user must enter
the EGP amount), `POSSIBLE_DUPLICATE`, `UNKNOWN_TYPE`.

**Balance rules** (`ledger/Ledger.java`, the only code that changes balances): money out = −(amount + fee), money in =
+(amount − fee). Each transaction has an `applied` flag, so a transaction is never counted twice. Edits reverse the old
effect before applying the new one, and rejects reverse it. The account row is locked (`SELECT … FOR UPDATE`) during every
change. Transfers between the user's own accounts are linked and excluded from spending (`Ledger.countsAsSpending`).
When the SMS shows the bank's balance, any difference from the app's balance is stored in `balance_difference`.

## Android setup (inside your React Native app)
1. Copy `android/app/src/main/java/com/financeapp/sms/*.java` to `android/app/src/main/java/<your/package>/sms/`.
2. Merge `android/AndroidManifest.additions.xml` into `android/app/src/main/AndroidManifest.xml` (permission +
   `SmsReceiver`), and add `implementation "androidx.work:work-runtime:2.9.1"` to `android/app/build.gradle`.
3. Register the package in `MainApplication.kt`:
   `override fun getPackages() = PackageList(this).packages.apply { add(SmsCapturePackage()) }`
   (written as a classic native module; it works through React Native's interop layer on the New Architecture).

## React Native usage
```ts
import { createSmsApi } from './sms/smsApi';
import { enableSmsCapture, onSmsEvents, updateSmsCaptureToken, disableSmsCapture } from './sms/smsCapture';

const api = createSmsApi(API_URL, getToken);              // your token getter

// After the user agrees on your explanation screen (proposal: clear consent):
const r = await enableSmsCapture(api, { baseUrl: API_URL, token }, {
  title: 'Read bank SMS?', message: 'Only messages from your banks and wallets are read. Codes (OTP) never leave your phone.', ok: 'Allow',
});                                                        // 'enabled' | 'denied' | 'blocked' | 'unsupported'

useEffect(() => onSmsEvents({ processed: () => { reloadBalances(); reloadReviewBadge(); } }), []);
// On token refresh: updateSmsCaptureToken(API_URL, newToken)   On sign-out: disableSmsCapture()
```
Screens: `<SmsReviewScreen api={api} accounts={accounts} lang="ar" onChanged={reloadBalances} />` and
`<SmsPasteScreen api={api} />`. The paste screen also works on iOS and on emulators, which is useful for demos.
To demo the receiver on an emulator, send an SMS from the emulator's extended controls, and first add that sender
number as a bank with `PUT /api/sms/senders`.

## Privacy and Google Play
- Only SMS from senders on the user's bank/wallet list are processed. All other SMS are skipped on the phone.
- OTP messages are dropped on the phone. The server stores the text of transactions only; OTPs, offers and alerts are
  kept as a hash. Data is filtered by user id everywhere.
- `RECEIVE_SMS` is a restricted permission on Google Play. Budget-tracking apps are listed as a possible exception
  ("SMS-based money management"), subject to Google's review and a declaration form. An APK installed directly for
  the graduation demo is not affected.

## Tests and checks (all run before delivery)
| Check | Result |
|---|---|
| Java parser vs Python model, 1,011 messages (dataset + hand-written + edge cases) | identical on every field, including confidence |
| `LedgerTest` (4), `SmsIngestFlowTest` (10), `SmsParserParityTest` (1) | 15/15 pass (run with in-memory repositories) |
| Full dataset through ingest + random confirms/rejects | every balance = opening + counted transactions |
| Phone OTP filter on 1,000 messages | 84/84 OTPs dropped, 0 other messages dropped; purchase alerts ending in "never share your OTP" kept |
| SQL migration on PostgreSQL 16 | runs, re-runs safely; constraints reject negative amounts, bad types, double SMS |
| Row lock, 30 simultaneous −10 EGP updates | with lock: 700 (correct); without: 930 (23 updates lost) |
| Backend and Android Java compiled against stand-in Spring/Android/React classes; TypeScript `--strict` | clean |

Not verified here (no Android SDK, Spring or React Native libraries offline): a real Gradle/Android build, a
running Spring context with Hibernate, and the app on a device. Run the tests in `backend/src/test` in your project
(they use JUnit 5 only), then try one SMS end to end on an emulator.

## Retraining the model with real SMS
```bash
cd model
python3 sms_model.py train your_labelled.jsonl sms_txn_model.joblib       # same JSONL schema as the dataset
python3 evaluate.py your_labelled.jsonl manifest.csv                     # needs a manifest with template ids/senders
python3 export_model.py sms_txn_model.joblib ../backend/src/main/resources/sms/sms-model.tsv.gz
python3 make_parity_fixture.py sms_txn_model.joblib your_labelled.jsonl ../backend/src/test/resources/sms/parity_fixture.tsv
```
The model was trained on 1,000 synthetic messages from 8 fictional senders. Real banks will word things differently,
so collect and label a few hundred real, anonymised SMS before relying on auto-confirm. Until then you can set
`app.sms.auto-confirm: false` so every SMS becomes a draft.
