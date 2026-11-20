import { DashboardSummary } from '@/types/dashboard';

/**
 * Sample data matching the "02 / Home Dashboard" Figma frame, so the dashboard
 * can be built and reviewed before the backend exists. Replace with the real
 * API client once it's ready — the screen only reads this shape.
 */
export const mockDashboardSummary: DashboardSummary = {
  periodLabel: 'Oct 2026',
  totalSalary: 30000,
  totalExpense: 12450,
  budgetLimit: 18000,
  primaryAccount: { name: 'CIB Account', balance: 20550 },
  cashBalance: 4000,
  recentTransactions: [
    { id: 'txn-1', merchant: 'Carrefour', category: 'groceries', date: '2026-10-28', amount: -850 },
    { id: 'txn-2', merchant: 'Uber', category: 'transport', date: '2026-10-28', amount: -120 },
    { id: 'txn-3', merchant: 'Vodafone', category: 'bills', date: '2026-10-28', amount: -250 },
  ],
};
