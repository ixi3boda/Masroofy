import * as Crypto from 'expo-crypto';
import { getAccounts } from '@/api/endpoints/accounts';
import { createTransaction } from '@/api/endpoints/transactions';
import { AccountResponse, TransactionResponse } from '@/api/types';
import { strings } from '@/strings';
import { TrackingAccount } from '@/types/sms';
import { Transaction, TransactionCategory, TransactionInput } from '@/types/transaction';
import { AppError } from '@/utils/errors';
import { TransactionService } from '../types';

/**
 * The real backend behind `TransactionService` (used when the transactions source is `api`).
 * The backend can add transactions (docs/frontend-api/12-add-transaction.md) but has no list,
 * edit or delete API yet, so the list here is what was saved in this session. Those screens
 * are switched off (`constants/features.ts`).
 */

const MAX_RECENT_SEARCHES = 5;

const pad = (value: number) => String(value).padStart(2, '0');

/** The device's local date, `YYYY-MM-DD`. */
const localToday = () => {
  const now = new Date();
  return `${now.getFullYear()}-${pad(now.getMonth() + 1)}-${pad(now.getDate())}`;
};

const toTrackingAccount = ({ id, name, cardLast4 }: AccountResponse): TrackingAccount => {
  const label = cardLast4 ? `${name} •${cardLast4}` : name;
  return { id, label, shortLabel: label, cardLast4 };
};

/** The same mapping as the dashboard's recent items (`apiDashboardService`). */
const toTransaction = ({ id, title, category, date, time, signedAmount, account, note }: TransactionResponse): Transaction => ({
  id,
  title,
  category: (category?.key ?? 'other') as TransactionCategory,
  date,
  time,
  amount: Number(signedAmount),
  accountId: account.id,
  note,
});

const newestFirst = (list: Transaction[]) => [...list].sort((a, b) => b.date.localeCompare(a.date));

let accounts: TrackingAccount[] = [];
let transactions: Transaction[] = [];
let recentSearches: string[] = [];

/**
 * The request id of the save being attempted. The same form sent again (Retry) keeps it, so the
 * server returns the first save instead of a second one; a changed form gets a new one.
 */
let pending: { input: string; id: string } | null = null;

const requestIdFor = (input: TransactionInput) => {
  const key = JSON.stringify(input);
  if (pending?.input !== key) pending = { input: key, id: Crypto.randomUUID() };
  return pending.id;
};

const notAvailable = async (): Promise<never> => {
  throw new AppError(strings.common.genericError);
};

export const apiTransactionService: TransactionService = {
  getTransactions: () => transactions,

  getTransaction: (id) => transactions.find((transaction) => transaction.id === id),

  getAccounts: () => accounts,

  async loadAccounts() {
    accounts = (await getAccounts()).map(toTrackingAccount);
    return accounts;
  },

  getToday: localToday,

  getRecentSearches: () => recentSearches,

  addRecentSearch(query) {
    const others = recentSearches.filter((recent) => recent.toLowerCase() !== query.toLowerCase());
    recentSearches = [query, ...others].slice(0, MAX_RECENT_SEARCHES);
  },

  async createTransaction(input) {
    if (!input.accountId) throw new AppError(strings.transactions.form.validation.account);
    const saved = toTransaction(
      await createTransaction({
        clientRequestId: requestIdFor(input),
        type: input.amount < 0 ? 'EXPENSE' : 'INCOME',
        amount: Math.abs(input.amount).toFixed(2),
        title: input.title,
        categoryKey: input.category,
        date: input.date,
        accountId: input.accountId,
        ...(input.note ? { note: input.note } : {}),
      })
    );
    pending = null;
    transactions = newestFirst([saved, ...transactions.filter(({ id }) => id !== saved.id)]);
    return saved;
  },

  updateTransaction: notAvailable,

  deleteTransaction: notAvailable,
};
