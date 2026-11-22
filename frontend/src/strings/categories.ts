import { TransactionCategory } from '@/types/transaction';

/** Display names for transaction categories. */
export const categoryStrings: Record<TransactionCategory, string> = {
  groceries: 'Groceries',
  transport: 'Transport',
  bills: 'Bills',
  rent: 'Rent',
  dining: 'Dining',
  health: 'Health',
  shopping: 'Shopping',
  other: 'Other',
  salary: 'Salary',
  freelance: 'Freelance',
  investment: 'Investment',
  gift: 'Gift',
  refund: 'Refund',
  otherIncome: 'Other Income',
};
