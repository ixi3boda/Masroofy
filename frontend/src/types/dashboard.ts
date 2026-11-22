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
  budgetLimit: number;
  primaryAccount: TrackedAccount;
  cashBalance: number;
  recentTransactions: Transaction[];
}
