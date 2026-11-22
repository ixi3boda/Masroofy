import { DashboardSummary } from '@/types/dashboard';

/** Figures of the "02 / Home Dashboard" Figma frame, before any change to the mock transactions. QA-only. */
export const mockDashboardSummary: Omit<DashboardSummary, 'recentTransactions'> = {
  periodLabel: 'Oct 2026',
  totalSalary: 30000,
  totalExpense: 12450,
  budgetLimit: 18000,
  primaryAccount: { name: 'CIB Account', balance: 20550 },
  cashBalance: 4000,
};
