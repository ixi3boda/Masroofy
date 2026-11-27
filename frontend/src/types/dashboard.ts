import { Transaction } from './transaction';

export interface TrackedAccount {
  name: string;
  balance: number;
}

export interface DashboardSummary {
  /** e.g. "Oct 2026" */
  periodLabel: string;
  totalSalary: number;
  totalExpense: number;
  /** 0 when the user has no budget. */
  budgetLimit: number;
  primaryAccount: TrackedAccount;
  cashBalance: number;
  /** Every account, converted to EGP. */
  currentBalance: number;
  recentTransactions: Transaction[];
  /** Captured transactions waiting for review (the SMS Detection dot). */
  pendingReview: number;
}
