import { CodeDelivery, UserProfile } from '@/types/auth';
import { ApiErrorDetails, FieldError } from '@/utils/errors';

/** Request and response bodies, as in docs/frontend-api/01…11. */

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
