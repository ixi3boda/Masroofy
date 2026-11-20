# Masroofy — Mobile app (React Native + Expo)

Personal finance app for Egypt (amounts in EGP). Built with **Expo SDK 58**, **Expo Router**, **TypeScript** and **Zustand**, following an **atomic design** component structure. Design source: the Masroofy Figma file (`Masroofy1`, page "Visual design light").

---

## 1. Project status

| Area | Status |
|---|---|
| **Reusable components** | ✅ **Almost all ready.** Every section of the Figma file (01 → 11) was reviewed and the components it needs are built, deduplicated and following atomic structure — 75 components in total. New screens should mostly be composition of existing pieces. |
| 01 · Welcome, Authentication & Onboarding | ✅ Screens built (8), running on mocks |
| 02 · Home Dashboard | ✅ Screen built, running on mocks |
| 03 · Transactions → 11 · Shared States | 🧩 Components ready, **screens not built yet** |
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
├── strings/        ALL user-facing text, grouped by feature (auth, dashboard, common, validation, categories)
├── constants/      Non-text app constants (currency, code length, resend cooldown, password rules)
├── navigation/     routes.ts — every route path (ROUTES.auth.login, ROUTES.app.home…)
├── services/       The ONLY data entry points screens use (authService, dashboardService)
├── mocks/          Fake data (mocks/data) + in-memory service implementations (mocks/services)
├── store/          Zustand stores (sessionStore = signed-in user)
├── hooks/          Reusable hooks (useGoBack, useHardwareBack, useCountdown)
├── types/          Shared domain types (auth, dashboard)
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

### Atoms (24)
`Avatar` · `Button` (primary / outline / danger / link / dangerLink, sizes md / sm) · `Card` (default / brand gradient) · `ChartBar` · `Checkbox` · `Chip` (info / success / error / warning, optional icon) · `Divider` · `Fab` · `Icon` (lucide, named set) · `IconBadge` (brand / error) · `IconButton` · `IconTile` · `Input` (label, hint, error, icons, multiline) · `OtpDigitBox` · `ProgressBar` (brand / danger) · `ProgressRing` · `Radio` · `SegmentedControl` · `SelectField` (tap-to-pick field) · `ShutterButton` · `Skeleton` · `Switch` · `Text` (`AppText`) · `Waveform`

### Molecules (29)
`ActionChip` · `AmountSummaryCard` (one big figure + header/children) · `BarChartColumn` · `BrandMark` · `DateRangeCard` · `DividedCard` (rows separated by dividers) · `DonutChart` · `EmailPreviewRow` · `FeedbackBanner` (info / success / error / warning) · `FieldRow` (side-by-side fields) · `InlineLoader` · `LegendItem` · `ListRow` (the universal row: settings, details, messages, quotes…) · `MonthTimeline` · `NotificationCard` · `OptionCard` (radio / checkbox) · `OtpCodeField` · `ProfileSummary` · `ProgressSummary` · `QuickActionTile` · `ReceiptPreview` · `RecentSearchItem` · `SectionHeader` · `SkeletonRow` · `StatCard` · `StateSummary` (hero / compact, brand / error) · `TabBarItem` · `TranscriptCard` · `TrendChart`

### Organisms (20)
`ActionChipGroup` · `AmountEntryCard` · `BottomTabBar` · `BudgetProgressCard` · `CapturePanel` (receipt camera) · `ConfirmDialog` · `GroupedBarChartCard` · `IncomeExpenseChartCard` · `OptionList` · `ProgressItemCard` (budgets / goals) · `QuickActionsGrid` · `RecentTransactions` · `ScreenHeader` · `SpendingBreakdownCard` · `StatCardRow` · `SummaryCard` · `TransactionGroupCard` · `TransactionItem` · `TransactionRecordCard` · `VoiceCaptureCard`

### Templates (1)
`ScreenLayout` — header (back / left / right slots, centered or start title) → keyboard-aware scroll body → optional sticky footer buttons and/or bottom tab bar.

### Which components each upcoming section uses

| Figma section | Main building blocks |
|---|---|
| 03 Transactions | `SegmentedControl`, `Input` (search), `TransactionGroupCard`, `AmountEntryCard`, `SelectField`, `OptionList`, `DateRangeCard`, `TransactionRecordCard`, `ReceiptPreview`, `ConfirmDialog`, `RecentSearchItem` |
| 04 SMS Capture | `Input` (multiline), `OptionCard` (checkbox), `DividedCard` + `ListRow` (messages, steps), `FeedbackBanner` (warning), `OptionList`, `TransactionRecordCard` |
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
- Use `useGoBack(ROUTES.x.y)` for header back buttons: it goes back when there is history and otherwise falls back to the given route (deep links, web refresh).
- Use `useHardwareBack(handler)` when the Android back button must do something custom (e.g. "Password updated" always returns to Login).
- After sign-in, the auth screens are removed from history by the guarded route groups, so back can never return to Login from inside the app.
