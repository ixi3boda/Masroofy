import { CodeDelivery, UserProfile } from '@/types/auth';
import { ApiErrorDetails, FieldError } from '@/utils/errors';

/** Request and response bodies, as in docs/frontend-api/01…12. */

/** The error body every endpoint uses (docs/frontend-api/00 §5). */
export interface ApiErrorBody {
  timestamp?: string;
  status?: number;
  code?: string;
  message?: string;
  path?: string;
  fieldErrors?: FieldError[];
  details?: ApiErrorDetails;
}

/** Login (API 4) and refresh (API 5). */
export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: 'Bearer';
  /** Access token lifetime in seconds. */
  expiresIn: number;
  user: UserProfile;
}

/** Register (API 1), `201`. */
export interface RegisterResponse {
  user: UserProfile;
  verification: CodeDelivery;
  verificationEmailSent: boolean;
}

/** Verify email (API 2), `200`. */
export interface VerifyEmailResponse {
  email: string;
  emailVerified: boolean;
}

/** Reset password (API 9), `200`. */
export interface MessageResponse {
  message: string;
}

/**
 * Home dashboard (API 11), `200`: the fields the app reads (all of them: docs/frontend-api/11-dashboard.md).
 * Money is a string, e.g. `"12450.00"`.
 */
export interface DashboardResponse {
  period: { month: string; label: string; timezone: string; asOf: string; currentMonth: boolean };
  baseCurrency: string;
  summary: { totalIncome: string; totalExpense: string; net: string };
  balance: {
    total: string;
    /** Largest `balanceInBase` first. */
    accounts: {
      id: string;
      name: string;
      type: 'cash' | 'card' | 'bank' | 'e_wallet';
      currency: string;
      balance: string;
      /** Absent when no exchange rate exists. */
      balanceInBase?: string;
    }[];
    unconvertedCurrencies: string[];
  };
  /** Absent when the user has no overall monthly budget. */
  budget?: { limit: string; spent: string; remaining: string; usedPercent: number; status: 'ON_TRACK' | 'NEAR_LIMIT' | 'OVER' };
  /** Newest first. */
  recentTransactions: {
    id: string;
    type: 'EXPENSE' | 'INCOME' | 'TRANSFER';
    title: string;
    note?: string;
    /** Absent for transfers. `key` is a `TransactionCategory`. */
    category?: { id: string; key: string; name: string };
    account: { id: string; name: string };
    /** Negative for expenses; absent for transfers. */
    signedAmount?: string;
    /** Local `YYYY-MM-DD` / `HH:mm`. */
    date: string;
    time: string;
  }[];
  badges: { pendingReview: number };
}

/** Add Transaction (API 14), request body. Money is a string, e.g. `"850.00"` (docs/frontend-api/12-add-transaction.md). */
export interface CreateTransactionRequest {
  /** One per draft; the same one again on Retry, so a retry never saves twice. */
  clientRequestId: string;
  type: 'EXPENSE' | 'INCOME';
  /** Positive, two decimals. */
  amount: string;
  title: string;
  /** A `TransactionCategory`. */
  categoryKey: string;
  /** `YYYY-MM-DD`, not in the future. */
  date: string;
  accountId: string;
  note?: string;
}

/** One income or expense (APIs 14 and 15): the same fields as the dashboard's recent transactions. */
export interface TransactionResponse {
  id: string;
  type: 'EXPENSE' | 'INCOME';
  title: string;
  note?: string;
  /** `key` is a `TransactionCategory`. */
  category?: { id: string; key: string; name: string };
  account: { id: string; name: string };
  amount: string;
  /** Negative for expenses. */
  signedAmount: string;
  currency: string;
  amountInBase: string;
  /** Local `YYYY-MM-DD` / `HH:mm` in the user's time zone. */
  date: string;
  time: string;
}

/** An account a transaction can be recorded against (API 12), oldest first. */
export interface AccountResponse {
  id: string;
  name: string;
  type: 'cash' | 'card' | 'bank' | 'e_wallet';
  currency: string;
  cardLast4?: string;
}
