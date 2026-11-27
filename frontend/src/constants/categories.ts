import type { IconName } from '@components/atoms/Icon';
import { ExpenseCategory, IncomeCategory, TransactionCategory, TransactionType } from '@/types/transaction';

const EXPENSE_CATEGORIES: ExpenseCategory[] = [
  'groceries',
  'transport',
  'bills',
  'rent',
  'dining',
  'health',
  'shopping',
  'other',
];

const INCOME_CATEGORIES: IncomeCategory[] = ['salary', 'freelance', 'investment', 'gift', 'refund', 'otherIncome'];

/** The categories of each transaction type, in picker order. */
export const CATEGORIES: Record<TransactionType, TransactionCategory[]> = {
  expense: EXPENSE_CATEGORIES,
  income: INCOME_CATEGORIES,
};

export const CATEGORY_ICONS: Record<TransactionCategory, IconName> = {
  groceries: 'groceries',
  transport: 'transport',
  bills: 'bills',
  rent: 'rent',
  dining: 'dining',
  health: 'health',
  shopping: 'shopping',
  other: 'other',
  salary: 'salary',
  freelance: 'laptop',
  investment: 'trending-up',
  gift: 'piggy-bank',
  refund: 'transfer',
  otherIncome: 'other',
};
