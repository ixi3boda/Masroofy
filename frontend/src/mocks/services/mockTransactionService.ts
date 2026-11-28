import { mockTrackingAccounts } from '@/mocks/data/smsMessages';
import { MOCK_FAILING_TITLE, MOCK_TODAY, mockRecentSearches, mockTransactions } from '@/mocks/data/transactions';
import { TransactionService } from '@/services/types';
import { strings } from '@/strings';
import { Transaction } from '@/types/transaction';
import { AppError } from '@/utils/errors';

/**
 * In-memory transactions, kept until the app reloads. Every write replaces the
 * list, so readers can compare by reference. Screens use
 * `@/services/transactionService`, never this file.
 */

const RESPONSE_DELAY_MS = 300;
const MAX_RECENT_SEARCHES = 5;

const wait = () => new Promise((resolve) => setTimeout(resolve, RESPONSE_DELAY_MS));
const newestFirst = (list: Transaction[]) => [...list].sort((a, b) => b.date.localeCompare(a.date));

let transactions = newestFirst(mockTransactions);
let recentSearches = mockRecentSearches;
let nextId = mockTransactions.length + 1;
let failedLastAttempt = false;

const findTransaction = (id: string) => transactions.find((transaction) => transaction.id === id);

/** The QA title fails on every other attempt, so Retry always succeeds. */
const simulateFailure = (title: string) => {
  if (title.toLowerCase() !== MOCK_FAILING_TITLE.toLowerCase()) return;
  failedLastAttempt = !failedLastAttempt;
  if (failedLastAttempt) throw new AppError(strings.common.genericError);
};

export const mockTransactionService: TransactionService = {
  getTransactions: () => transactions,

  getTransaction: findTransaction,

  getAccounts: () => mockTrackingAccounts,

  loadAccounts: async () => mockTrackingAccounts,

  getToday: () => MOCK_TODAY,

  getRecentSearches: () => recentSearches,

  addRecentSearch(query) {
    const others = recentSearches.filter((recent) => recent.toLowerCase() !== query.toLowerCase());
    recentSearches = [query, ...others].slice(0, MAX_RECENT_SEARCHES);
  },

  async createTransaction(input) {
    await wait();
    simulateFailure(input.title);
    const created = { ...input, id: `txn-${nextId++}` };
    transactions = newestFirst([created, ...transactions]);
    return created;
  },

  async updateTransaction(id, input) {
    await wait();
    const existing = findTransaction(id);
    if (!existing) throw new AppError(strings.common.genericError);
    simulateFailure(input.title);
    const updated = { ...existing, ...input };
    transactions = newestFirst(transactions.map((transaction) => (transaction.id === id ? updated : transaction)));
    return updated;
  },

  async deleteTransaction(id) {
    await wait();
    transactions = transactions.filter((transaction) => transaction.id !== id);
  },
};
