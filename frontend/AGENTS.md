This is an Expo/React Native mobile application. Prioritize mobile-first patterns, performance, and cross-platform compatibility.

## Expo has changed — do not trust your training data

Expo ships breaking changes every SDK release. APIs you remember are likely renamed, moved, or removed. Before writing any code that touches an Expo, EAS, or React Native API:

1. Read the major version of the `expo` package in `package.json`.
2. Fetch the matching versioned docs: `https://docs.expo.dev/versions/v<major>.0.0/`
3. For anything else, fetch https://docs.expo.dev/llms.txt — an index of all Expo docs with corrections to common LLM misconceptions. Follow its links to the specific page you need; never answer from memory.

## Commands

Use `bunx` instead of `npx` if the project uses bun (`bun.lock` present).

```bash
npx expo install <package>  # ALWAYS use instead of npm/yarn/pnpm/bun add — resolves SDK-compatible versions
npx expo start              # start the dev server
npx expo lint               # lint
npx tsc --noEmit            # typecheck
npx expo-doctor             # diagnose dependency and config issues
npx expo install --fix      # fix incompatible package versions
```

Run lint and typecheck before declaring any task done.

## Navigation & Routing

- Use **Expo Router** for all navigation. Routes live in `src/app/` — every file there is a thin route file that just re-exports the real screen component (`export { default } from '@screens/XScreen'`). `_layout.tsx` files define navigators. Keep non-route code (components, hooks, utils) outside `src/app/`.
- Import `Link`, `router`, and `useLocalSearchParams` from `expo-router`.
- Docs: https://docs.expo.dev/router/introduction.md

## Project structure & conventions

- **One `screens` folder.** Every screen component lives flat in `src/screens/` (e.g. `src/screens/LoginScreen.tsx`), regardless of which flow/feature it belongs to. Route files in `src/app/` stay thin wrappers that import from `@screens/*` — all layout, state, and logic for a screen lives in its `src/screens` file.
- **Component library is (almost) complete.** All Figma sections (01–11) have been reviewed and their reusable components built — see `README.md` §4 for the full inventory and which components each upcoming section uses. Build new screens by composing these; only add a component for a genuine gap.
- **Reusable components, strictly.** Before writing new UI, check `src/components/{atoms,molecules,organisms,templates}` for something that already does the job. Extend or compose an existing component instead of duplicating markup/styles inline in a screen. Only add a new component when nothing in the tree already covers it.
- **Atomic structure, strictly.** `src/components` stays organized as atoms → molecules → organisms → templates, each layer composed only from the layer(s) below it:
  - `atoms`: smallest building blocks (Text, Button, Input, Icon, Chip…), no business logic.
  - `molecules`: small compositions of atoms (BrandMark, SummaryCard, OtpCodeField…).
  - `organisms`: larger, often screen-section-sized compositions (AuthHeader…).
  - `templates`: page-level layout shells screens plug content into (AuthScreenLayout…).
  - Screens (`src/screens`) compose templates/organisms/molecules/atoms — they should not reimplement layout primitives those layers already provide.
- **Where things live (`src/`).** Never hard-code these in screens or components:
  - `theme/` — design tokens: colors, typography, spacing, radii, shadows, gradients.
  - `strings/` — all user-facing copy, grouped by feature (`auth`, `dashboard`, `common`, `validation`, `categories`), read via `strings.<feature>.<key>`. Dynamic copy is a function, e.g. `strings.common.resendCodeIn(30)`.
  - `constants/` — non-copy app constants (currency, code length, cooldowns, password rules).
  - `navigation/routes.ts` — every route path (`ROUTES.auth.login`); screens never write URL strings.
  - `types/` — shared domain types.
  - `utils/` — pure helpers (formatters, validators, `AppError` / `getErrorMessage`).
  - `hooks/` — reusable hooks. `store/` — Zustand stores.
  - `mocks/` — all fake data (`mocks/data`) and in-memory service implementations (`mocks/services`). Kept for testing; do not delete.
  - `services/` — the only data entry points screens import (`authService`, `dashboardService`). Each one picks its mock (`mocks/services`) or its API implementation (`services/api`) from config, per service, via `EXPO_PUBLIC_API_MODE` / `EXPO_PUBLIC_<NAME>_SOURCE`. Both implement the same interface (`services/types.ts`) and the backend contract, so screens stay unchanged in either mode. Services throw `AppError` (or its subclass `ApiError`, with the backend `code`) for user-safe messages. Rules: `../docs/frontend-api/00-instructions-for-claude.md` §3; status: `../docs/frontend-api/integration-plan.md`.
  - `config/` — `env.ts`, the only file that reads `process.env` (`EXPO_PUBLIC_*`, from `.env.local`; template `.env.example`).
  - `api/` — the HTTP layer for the real backend: client, tokens, refresh, one function per endpoint. Only `services/api/*` imports it.
- **State management: Zustand.** Use a Zustand store (`src/store`) for any state shared across screens/components (session/auth state, in-progress multi-step flows, anything that needs to survive navigation). Local `useState`/`useReducer` is fine for state that belongs to a single screen or component and nothing else — don't reach for Zustand for that.
- **Clean code, strictly.** No dead code, no unused exports/props, no commented-out blocks, no speculative abstractions for things you don't need yet. Keep components small and single-purpose; prefer composition over large multi-responsibility components or screens.
- **Memoize when it actually helps.** Reach for `useMemo` / `useCallback` / `React.memo` when a component re-renders often with expensive children, or when a stable reference is needed to avoid re-rendering children (e.g. callbacks passed to `FlatList` items) — not reflexively on every component/function.

## Building with EAS

Use EAS to build, sign, and submit the app in the cloud (`eas build`, `eas submit`) and to ship over-the-air updates (`eas update`) — no local Xcode or Android Studio required. Run EAS CLI as `bunx eas-cli <command>` in Bun projects, or `npx eas-cli@latest <command>` otherwise; substitute that for bare `eas` in docs examples.
Docs: https://docs.expo.dev/eas/index.md

## Rules

- If `ios/` and `android/` directories do not exist, they are generated (Continuous Native Generation). Never create or edit them by hand — configure native behavior in `app.json` and config plugins.
- Expo Go only includes its bundled native modules. After adding a library with native code, the app needs a development build: `npx expo run:ios|android` locally, or `eas build --profile development`.
- Prefer recommended Expo modules over third-party libraries, and check your available skills before adding dependencies. Docs: https://docs.expo.dev/versions/latest/index.md
