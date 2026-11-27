import { CATEGORY_ICONS } from '@/constants/categories';
import { strings } from '@/strings';
import { TrackingAccount } from '@/types/sms';
import {
  Transaction,
  TransactionDraft,
  TransactionDraftErrors,
  TransactionFilters,
  TransactionInput,
  TransactionType,
} from '@/types/transaction';
import {
  formatCurrency,
  formatDate,
  formatExactNumber,
  formatLongDate,
  formatSignedCurrency,
  parseDate,
} from '@/utils/formatters';
import { parseAmount } from '@/utils/validators';

const copy = strings.transactions;

export const getTransactionType = ({ amount }: Pick<Transaction, 'amount'>): TransactionType =>
  amount < 0 ? 'expense' : 'income';

/** Title, category icon and amount, as every transaction row and record card shows them. */
export const toTransactionRow = (transaction: Transaction) => ({
  id: transaction.id,
  title: transaction.title,
  icon: CATEGORY_ICONS[transaction.category],
  amount: formatSignedCurrency(transaction.amount),
});

/** The history list: one section per date, with that date's expenses and income on separate cards. */
export const groupByDay = (transactions: Transaction[], accounts: TrackingAccount[]) => {
  const byDate = new Map<string, Transaction[]>();
  for (const transaction of transactions) {
    byDate.set(transaction.date, [...(byDate.get(transaction.date) ?? []), transaction]);
  }

  const toRow = (transaction: Transaction) => {
    const account = accounts.find(({ id }) => id === transaction.accountId)?.shortLabel;
    const type = getTransactionType(transaction) === 'expense' ? copy.types.expense : undefined;
    const meta = [type, strings.categories[transaction.category], account].filter(Boolean).join(' · ');
    return { ...toTransactionRow(transaction), meta };
  };

  return Array.from(byDate, ([date, entries]) => ({
    date,
    title: formatLongDate(date),
    expenses: entries.filter(({ amount }) => amount < 0).map(toRow),
    income: entries.filter(({ amount }) => amount > 0).map(toRow),
  }));
};

export const filterTransactions = (
  transactions: Transaction[],
  { from, to, type, category, accountId }: TransactionFilters,
) =>
  transactions.filter(
    (transaction) =>
      transaction.date >= from &&
      transaction.date <= to &&
      (type === 'all' || getTransactionType(transaction) === type) &&
      (category === 'all' || transaction.category === category) &&
      (accountId === 'all' || transaction.accountId === accountId),
  );

/** Matches merchant / title and note, or the amount with or without separators. */
export const searchTransactions = (transactions: Transaction[], query: string) => {
  const term = query.trim().toLowerCase();
  if (!term) return [];
  return transactions.filter(({ title, note = '', amount }) => {
    const value = Math.abs(amount);
    return [title, note, String(value), formatExactNumber(value), formatCurrency(value)].some((text) =>
      text.toLowerCase().includes(term),
    );
  });
};

export const toTransactionDraft = (transaction: Transaction): TransactionDraft => ({
  amount: formatExactNumber(Math.abs(transaction.amount)),
  title: transaction.title,
  category: transaction.category,
  date: formatDate(transaction.date),
  accountId: transaction.accountId ?? null,
  note: transaction.note ?? '',
});

/** The input to save, or the message for each field that stops it being saved. */
export const parseTransactionDraft = (
  draft: TransactionDraft,
  type: TransactionType,
  accountRequired: boolean,
): { input: TransactionInput } | { errors: TransactionDraftErrors } => {
  const { validation } = copy.form;
  const amount = parseAmount(draft.amount);
  const title = draft.title.trim();
  const date = parseDate(draft.date);
  const accountMissing = accountRequired && !draft.accountId;

  if (amount !== null && title && draft.category && date && !accountMissing) {
    return {
      input: {
        amount: type === 'expense' ? -amount : amount,
        title,
        category: draft.category,
        date,
        accountId: draft.accountId ?? undefined,
        note: draft.note.trim() || undefined,
      },
    };
  }

  return {
    errors: {
      amount: amount === null ? copy.form[type].amountError : undefined,
      title: title ? undefined : copy.form[type].titleError,
      category: draft.category ? undefined : validation.category,
      date: date ? undefined : validation.date,
      accountId: accountMissing ? validation.account : undefined,
    },
  };
};
