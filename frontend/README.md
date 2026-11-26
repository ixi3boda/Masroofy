# Masroofy — Mobile app (React Native + Expo)

Personal finance app for Egypt (amounts in EGP). Built with **Expo SDK 58**, **Expo Router**, **TypeScript** and **Zustand**, following an **atomic design** component structure. Design source: the Masroofy Figma file (`Masroofy1`, page "Visual design light").

---

## 1. Project status

| Area | Status |
|---|---|
| **Reusable components** | ✅ **Almost all ready.** Every section of the Figma file (01 → 11) was reviewed and the components it needs are built, deduplicated and following atomic structure — 80 components in total. New screens should mostly be composition of existing pieces. |
| 01 · Welcome, Authentication & Onboarding | ✅ Screens built (8), running on mocks |
| 02 · Home Dashboard | ✅ Screen built, running on mocks |
| 03 · Transactions | ✅ Screens built (9 screens for the 18 frames), running on mocks — see §2 |
| 04 · SMS Capture | ✅ Screens built (9 screens for the 10 frames), running on mocks — see `src/screens/Sms*` |
| 05 · Receipt Scanning → 11 · Shared States | 🧩 Components ready, **screens not built yet** |
| Backend / API | ⏳ Not connected. The app runs fully on in-memory mocks (see §5) |

---

## 2. Running the app

```bash
cd frontend
npm install
npx expo start          # then press w (web), a (Android) or i (iOS)
npx expo lint           # lint
npx tsc --noEmit --ignoreDeprecations 6.0   # typecheck
```

> The `--ignoreDeprecations 6.0` flag is needed until `baseUrl` is removed from `tsconfig.json` (deprecated in TypeScript 6). Three known type errors remain in `OtpDigitBox` / `OtpCodeField` (TextInput ref typing) — they don't affect runtime.

Always add packages with `npx expo install <package>` (keeps versions compatible with the Expo SDK).

### Test accounts (mock mode)

| Email | Password | Use for |
|---|---|---|
| `demo@masroofy.app` | `Passw0rd!` | Log in happy path |
| `taken@masroofy.app` | `Passw0rd!` | "Email already exists" on sign-up |
| `a@masroofy.app` | `Passw0rd!` | Masked-email edge case |

Verification / password-reset code everywhere: **`123456`**. These live in `src/mocks/data/authAccounts.ts`.

### Transactions is partly closed for now

Only adding is open: Add Transaction and the **+** button (Home and Bank Messages) work. The rest is visible but unclickable (Home: View All, recent transactions; Bank Messages: View existing transaction). SMS is open. Switches live in `src/constants/features.ts` (`addTransaction`, `transactions`); the Transactions guide below assumes both are open.

### Transactions (mock mode)

Open from Home: **Add Transaction** / the **+** button, **View All**, or any recent transaction. "Today" is 28 Oct 2026, so the sample month matches Figma. Adds, edits and deletes update Home's totals and balances and reset when the app reloads.

| Frames | Screen (`/transactions/…`) | How to reach it |
|---|---|---|
| 03-01 | `list` | Home → View All |
| 03-02 | `filters` | All Transactions → Filters |
| 03-03, 03-04 | `filtered` | Groceries + Expense → Apply · Groceries + Income → Apply (no match) |
| 03-05, 03-05B | `details` | Tap any transaction · Delete transaction |
| 03-05A, 03-05B, 03-05C | `edit` | Details → Edit transaction · change a field, then Cancel |
| 03-06, 03-08, 03-10, 03-12, 03-14 | `add` (`?tab=income`) | Expense / Income tabs · save with an empty amount · save with the merchant **`Retry test`** (fails once, Retry works) |
| 03-07, 03-11 | `category` | Add or Edit → Category |
| 03-09, 03-13 | `saved` | Save a valid entry |
| 03-17 | `search` | All Transactions → Search transactions |

### SMS capture (mock mode)

Log in, then tap **SMS Detection** on Home. Three sample bank messages (`src/mocks/data/smsMessages.ts`) cover every review path:

| Message | Opens | Why |
|---|---|---|
| CIB · EGP 850 at Carrefour | 04-04 → 04-05 | Same amount, merchant, card and day as the Carrefour expense on Home → confirm links it, no duplicate |
| NBE · EGP 500 cash withdrawal | 04-07 → 04-08 | Withdrawals must be classified (cash / transfer / needs clarification) |
| Banque Misr · EGP 240 at Electricity | 04-06 → 04-08 | No matching record, card not mapped to an account → user verifies everything |

"Import a bank SMS" parses any pasted text with an amount (`EGP 120.00`) and a date (`28/10/2026 09:05`), e.g. `Your card ending 4821 was used for EGP 120.00 at UBER on 28/10/2026 09:05.` (matches the Uber expense). Text without them opens 04-10. "Share a selected message" fills in a sample message. Statuses reset when the app reloads.

---

## 3. Folder structure (`src/`)

```
src/
├── app/            Expo Router routes — thin files that re-export a screen
├── screens/        One file per screen (all layout, state and logic for that screen)
├── components/     Reusable UI, atomic design (see §4)
│   ├── atoms/
│   ├── molecules/
│   ├── organisms/
│   └── templates/
├── theme/          Design tokens: colors, typography, spacing, radii, shadows, gradients
├── strings/        ALL user-facing text, grouped by feature (auth, dashboard, sms, transactions, common, validation, categories)
├── constants/      Non-text app constants (currency, code length, resend cooldown, password rules)
├── navigation/     routes.ts — every route path (ROUTES.auth.login, ROUTES.app.home…)
├── services/       The ONLY data entry points screens use (authService, dashboardService, smsService, transactionService)
├── mocks/          Fake data (mocks/data) + in-memory service implementations (mocks/services)
├── store/          Zustand stores (sessionStore = signed-in user, smsReviewStore = SMS review in progress, transactionDraftStore / transactionFilterStore = section 03 forms)
├── hooks/          Reusable hooks (useGoBack, useHardwareBack, useCountdown, useTabParam, useServiceData…)
├── types/          Shared domain types (auth, dashboard, sms, transaction)
└── utils/          Pure helpers (formatters, validators, AppError / getErrorMessage)
```

### Rules — never hard-code these in screens or components

| Need | Use |
|---|---|
| A color, font size, spacing, radius, shadow | `@theme/index` → `colors`, `typography`, `spacing`, `radii`, `shadows` |
| Any text the user sees | `strings.<feature>.<key>` from `@/strings` (dynamic text is a function: `strings.common.resendCodeIn(30)`) |
| A route path | `ROUTES.<group>.<screen>` from `@/navigation/routes` |
| A fixed number / rule | `@/constants/app` |
| Data from the backend | a service in `@/services/*` — never import from `@/mocks` in a screen (only exception: on-screen QA hints like the demo login text) |
| A user-facing error message | `getErrorMessage(error)` from `@/utils/errors` |
| Back button behavior | `useGoBack(fallbackRoute)` / `useHardwareBack(handler)` from `@/hooks/useBackNavigation` |

---

## 4. Component library (atomic design)

Layering rule: **atoms** import only atoms · **molecules** import only atoms · **organisms** may use molecules, atoms and other organisms · **templates** are page shells. Every layer has an `index.ts` barrel.

Before building any UI, look here first — extend an existing component instead of creating a near-duplicate.

### Atoms (25)
`Avatar` · `Button` (primary / outline / danger / link / dangerLink, sizes md / sm) · `Card` (default / brand gradient) · `ChartBar` · `Checkbox` · `Chip` (info / success / error / warning, optional icon) · `Divider` · `Fab` · `Icon` (lucide, named set) · `IconBadge` (brand / error) · `IconButton` · `IconTile` · `Input` (label, hint, error, icons, multiline) · `OtpDigitBox` · `ProgressBar` (brand / danger) · `ProgressRing` · `Radio` · `SegmentedControl` (sliding highlight; `scrollable` inside scrolling content) · `SelectField` (tap-to-pick field, optional icon) · `ShutterButton` · `Skeleton` · `Switch` · `TabPanel` (animated body of the selected tab) · `Text` (`AppText`) · `Waveform`

### Molecules (29)
`ActionChip` · `AmountSummaryCard` (one big figure + header/children) · `BarChartColumn` · `BrandMark` · `DateRangeCard` · `DividedCard` (rows separated by dividers) · `DonutChart` · `EmailPreviewRow` · `FeedbackBanner` (info / success / error / warning) · `FieldRow` (side-by-side fields) · `InlineLoader` · `LegendItem` · `ListRow` (the universal row: settings, details, messages, quotes…) · `MonthTimeline` · `NotificationCard` · `OptionCard` (radio / checkbox) · `OtpCodeField` · `ProfileSummary` · `ProgressSummary` · `QuickActionTile` · `ReceiptPreview` · `RecentSearchItem` · `RequirementList` (live rule checklist, e.g. password) · `SectionHeader` · `SkeletonRow` · `StatCard` · `StateSummary` (hero / compact, brand / error) · `TabBarItem` · `TranscriptCard` · `TrendChart`

### Organisms (25)
`ActionChipGroup` · `AmountEntryCard` · `BankMessageCard` (imported SMS in the messages list) · `BottomTabBar` · `BudgetProgressCard` · `CapturePanel` (receipt camera) · `ConfirmDialog` · `DeleteTransactionDialog` · `DetailList` (key–value block) · `GroupedBarChartCard` · `IncomeExpenseChartCard` · `OptionList` · `ProgressItemCard` (budgets / goals) · `QuickActionsGrid` · `RecentTransactions` · `ScreenHeader` · `SpendingBreakdownCard` · `StatCardRow` · `SummaryCard` · `TransactionForm` (add / edit fields) · `TransactionGroupCard` · `TransactionHistory` (dated groups) · `TransactionItem` · `TransactionRecordCard` · `VoiceCaptureCard`

### Templates (1)
`ScreenLayout` — header (back / left / right slots, centered or start title) → optional pinned `toolbar` (e.g. tabs; `scrollKey` scrolls back to top when the tab changes) → keyboard-aware scroll body → optional sticky footer buttons and/or bottom tab bar.

**Tabbed screens** (e.g. Bank Messages): get the tab from `useTabParam(TAB_ORDER)`, put the `SegmentedControl` in `toolbar`, pass the tab as `scrollKey`, and wrap the tab's content in `<TabPanel index={…}>` so it slides in from the chosen side. Keep the footer and tab bar the same on every tab.

### Which components each upcoming section uses

| Figma section | Main building blocks |
|---|---|
| 03 Transactions ✅ | `SegmentedControl`, `Input` (search), `TransactionGroupCard`, `AmountEntryCard`, `SelectField`, `OptionList`, `DateRangeCard`, `TransactionRecordCard`, `ReceiptPreview`, `ConfirmDialog`, `RecentSearchItem` |
| 04 SMS Capture ✅ | `BankMessageCard`, `Input` (multiline), `OptionCard` (checkbox), `DividedCard` + `ListRow` (messages, steps), `FeedbackBanner` (warning), `OptionList`, `SelectField`, `StateSummary`, `TransactionRecordCard` |
| 05 Receipt Scanning | `CapturePanel`, `ReceiptPreview`, `OptionCard`, `DividedCard`, `StateSummary` (error tone) |
| 06 Voice Transactions | `VoiceCaptureCard`, `TranscriptCard`, `SegmentedControl`, `TransactionRecordCard` |
| 07 Budgets & Planning | `ProgressItemCard`, `AmountSummaryCard`, `ProgressSummary`, `ListRow` + `Switch`, `ProgressRing`, `MonthTimeline`, `OptionList` |
| 08 Insights & Reports | `SpendingBreakdownCard`, `GroupedBarChartCard`, `AmountSummaryCard`, `Chip` (trend icon) |
| 09 Stocks & Gold | `TrendChart`, `AmountSummaryCard`, `DividedCard` + `ListRow` (quotes), `SegmentedControl` (1W/1M/3M/1Y), `StateSummary` (compact) |
| 10 Notifications & Settings | `NotificationCard`, `ProfileSummary`, `DividedCard` + `ListRow` (+ `Switch` / `Radio` / chevron), `FieldRow`, `AmountSummaryCard` |
| 11 Shared States | `StateSummary`, `Skeleton`, `SkeletonRow`, `InlineLoader`, `DividedCard` |

**Known gaps (intentionally not componentized):** the decorative barcode on the receipt slip and the one-off "first use" illustration on the empty Home state — build those inside the screen when needed.

---

## 5. Connecting the backend — instructions

The app is already shaped so the backend can be plugged in **without touching any screen**. Everything currently runs on mocks; **keep the mocks** (they are used for testing).

### How data flows today

```
Screen ──► src/services/authService.ts ──► src/mocks/services/mockAuthService.ts
Screen ──► src/services/dashboardService.ts ──► src/mocks/data/dashboard.ts
```

Screens only ever import from `src/services/*`. The service file decides where the data comes from.

### Step by step

1. **Add the API base URL** as an Expo public env variable, e.g. in `frontend/.env.local` (git-ignored):
   ```
   EXPO_PUBLIC_API_URL=https://your-backend.example.com
   ```
   Read it with `process.env.EXPO_PUBLIC_API_URL`.

2. **Implement the real service** next to the existing one, keeping the **exact same method names, parameters and return types** as the mock. The contract the screens rely on:

   **`authService`** (`src/services/authService.ts`, types in `src/types/auth.ts`)

   | Method | Returns | Used by |
   |---|---|---|
   | `signUp({ fullName, email, password })` | `{ email }` | Sign up |
   | `verifySignUpCode(email, code)` | `AuthUser` (`{ fullName, email }`) — user is signed in after this | Verify email |
   | `resendSignUpCode(email)` | `void` | Verify email |
   | `logIn(email, password)` | `AuthUser` | Log in |
   | `requestPasswordReset(email)` | `{ email }` | Forgot password |
   | `verifyResetCode(email, code)` | `{ email }` | Check email |
   | `resendResetCode(email)` | `void` | Check email |
   | `resetPassword(email, newPassword)` | `{ email }` | Set new password |

   **`dashboardService`** (`src/services/dashboardService.ts`, types in `src/types/dashboard.ts`)

   | Method | Returns |
   |---|---|
   | `getSummary()` | `DashboardSummary` |

   > ⚠️ `getSummary()` is **synchronous** today because the mock is. A real request is async — change it to `async getSummary(): Promise<DashboardSummary>` and give `DashboardScreen` a loading state (`SkeletonRow` / `InlineLoader`) and an error state (`StateSummary` with `tone="error"`).

3. **Errors:** when the backend returns a message that is safe to show the user, throw `new AppError(message)` (from `src/utils/errors.ts`). Screens already display it via `getErrorMessage(error)`; anything else shows the generic "Something went wrong" text.

4. **Switch the service over** — change the single export line in the service file, e.g.:
   ```ts
   // src/services/authService.ts
   export const authService = httpAuthService; // was: mockAuthService
   ```
   To keep testing on mocks, just point it back. Do **not** delete `src/mocks/`.

5. **Auth session / tokens:** the signed-in user is stored in `src/store/sessionStore.ts` (`signIn(user)`), and the root layout (`src/app/_layout.tsx`) uses it to guard the `(auth)` and `(app)` route groups. If the backend returns an access token, add it to this store (and persist it with `expo-secure-store` if sessions should survive app restarts).

6. **New endpoints for future screens:** add a new file in `src/services/` (e.g. `transactionsService.ts`) with its types in `src/types/`. Optionally add matching fake data in `src/mocks/` so the screen can be built and tested before the endpoint exists.

7. **Verify:** `npx expo lint`, `npx tsc --noEmit`, then run through sign-up → verify → home, log in (right and wrong password) and the forgot-password flow.

---

## 6. Navigation & back button

- Routes live in `src/app/` and are listed in `src/navigation/routes.ts` — add new screens to both.
- Navigate with `router` from `@/navigation/router` (not `expo-router`): it ignores a second tap within 400 ms, so a double-tap opens or closes one screen, not two.
- Use `useGoBack(ROUTES.x.y)` for header back buttons: it goes back when there is history and otherwise falls back to the given route (deep links, web refresh).
- Use `useHardwareBack(handler)` when the Android back button must do something custom (e.g. "Password updated" always returns to Login) It only listens while its screen is focused, so screens pushed on top keep the normal back.
- In multi-step flows, `router.replace` a step that should not be returned to (SMS: Import → Processing → Review), so the plain back arrow and Android back already land on the right screen.
- After sign-in, the auth screens are removed from history by the guarded route groups, so back can never return to Login from inside the app.
