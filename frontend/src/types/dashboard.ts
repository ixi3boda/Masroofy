export type TransactionCategory = 'groceries' | 'transport' | 'bills';

export interface Transaction {
  id: string;
  merchant: string;
  category: TransactionCategory;
  /** ISO calendar date, `YYYY-MM-DD`. */
  date: string;
  /** Signed amount in EGP — negative for expenses, positive for income. */
  amount: number;
}

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
