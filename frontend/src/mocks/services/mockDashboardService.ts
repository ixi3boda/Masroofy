import { mockDashboardSummary } from '@/mocks/data/dashboard';
import { mockTrackingAccounts } from '@/mocks/data/smsMessages';
import { MOCK_TODAY, mockTransactions } from '@/mocks/data/transactions';
import { mockTransactionService } from '@/mocks/services/mockTransactionService';
import { DashboardService } from '@/services/types';
import { DashboardSummary } from '@/types/dashboard';
import { Transaction } from '@/types/transaction';

/**
 * Home totals = the Figma figures + whatever changed in the mock transactions.
 * The sample records don't itemise all of October, so totals can't be summed from them.
 */

const RECENT_COUNT = 3;
const CURRENT_MONTH = MOCK_TODAY.slice(0, 7);
const [PRIMARY_ACCOUNT, CASH] = mockTrackingAccounts;

const isCurrentExpense = ({ amount, date }: Transaction) => amount < 0 && date.startsWith(CURRENT_MONTH);
const isCurrentIncome = ({ amount, date }: Transaction) => amount > 0 && date.startsWith(CURRENT_MONTH);

const sumOf = (list: Transaction[], include: (transaction: Transaction) => boolean) =>
  list.reduce((total, transaction) => (include(transaction) ? total + transaction.amount : total), 0);

const getSummary = (): DashboardSummary => {
  const transactions = mockTransactionService.getTransactions();
  const changeIn = (include: (transaction: Transaction) => boolean) =>
    sumOf(transactions, include) - sumOf(mockTransactions, include);
  const { totalSalary, totalExpense, primaryAccount, cashBalance } = mockDashboardSummary;
  const primaryBalance = primaryAccount.balance + changeIn(({ accountId }) => accountId === PRIMARY_ACCOUNT.id);
  const cash = cashBalance + changeIn(({ accountId }) => accountId === CASH.id);

  return {
    ...mockDashboardSummary,
    totalSalary: totalSalary + changeIn(isCurrentIncome),
    totalExpense: totalExpense - changeIn(isCurrentExpense),
    primaryAccount: { ...primaryAccount, balance: primaryBalance },
    cashBalance: cash,
    currentBalance: primaryBalance + cash,
    recentTransactions: transactions.slice(0, RECENT_COUNT),
  };
};

export const mockDashboardService: DashboardService = {
  getSummary,
  loadSummary: async () => getSummary(),
};
