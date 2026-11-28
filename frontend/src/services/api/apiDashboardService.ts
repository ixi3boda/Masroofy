import { getDashboard } from '@/api/endpoints/dashboard';
import { DashboardResponse } from '@/api/types';
import { DashboardSummary } from '@/types/dashboard';
import { TransactionCategory } from '@/types/transaction';
import { DashboardService } from '../types';

const RECENT_COUNT = 3;
/** More than shown, because transfers are dropped: the app has no transfer row yet. */
const RECENT_LIMIT = 10;

const EMPTY_SUMMARY: DashboardSummary = {
  periodLabel: '',
  totalSalary: 0,
  totalExpense: 0,
  budgetLimit: 0,
  primaryAccount: { name: '', balance: 0 },
  cashBalance: 0,
  currentBalance: 0,
  recentTransactions: [],
  pendingReview: 0,
};

type Account = DashboardResponse['balance']['accounts'][number];

/** Server money is a string ("12450.00"); numbers here are for display only. */
const inBase = (account: Account | undefined) => Number(account?.balanceInBase ?? 0);

const toSummary = ({ period, summary, balance, budget, recentTransactions, badges }: DashboardResponse) => {
  const [primary] = balance.accounts; // largest balance first
  const cash = balance.accounts.find(({ type }) => type === 'cash');

  return {
    periodLabel: period.label,
    totalSalary: Number(summary.totalIncome),
    totalExpense: Number(summary.totalExpense),
    budgetLimit: budget ? Number(budget.limit) : 0,
    primaryAccount: { name: primary?.name ?? '', balance: inBase(primary) },
    cashBalance: inBase(cash),
    currentBalance: Number(balance.total),
    recentTransactions: recentTransactions
      .filter(({ type }) => type !== 'TRANSFER')
      .slice(0, RECENT_COUNT)
      .map(({ id, title, category, date, time, signedAmount, account, note }) => ({
        id,
        title,
        category: (category?.key ?? 'other') as TransactionCategory,
        date,
        time,
        amount: Number(signedAmount),
        accountId: account.id,
        note,
      })),
    pendingReview: badges.pendingReview,
  } satisfies DashboardSummary;
};

let latest = EMPTY_SUMMARY;

/** The real backend behind `DashboardService` (used when the dashboard source is `api`). */
export const apiDashboardService: DashboardService = {
  getSummary: () => latest,
  async loadSummary() {
    latest = toSummary(await getDashboard(RECENT_LIMIT));
    return latest;
  },
};
