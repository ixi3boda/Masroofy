import { Transaction } from '@/types/transaction';

/** "Today" in mock mode, so the sample month stays October 2026. QA-only. */
export const MOCK_TODAY = '2026-10-28';

/** Saving a transaction with this merchant or title fails once, then works on Retry (03-14). QA-only. */
export const MOCK_FAILING_TITLE = 'Retry test';

/** What the Search screen lists before anything is searched. QA-only. */
export const mockRecentSearches = ['Carrefour', 'Uber', 'October salary'];

/** The existing records of the "03 / Transactions" Figma frames, newest first. QA-only. */
export const mockTransactions: Transaction[] = [
  {
    id: 'txn-1',
    title: 'Carrefour',
    category: 'groceries',
    date: '2026-10-28',
    time: '14:32',
    amount: -850,
    accountId: 'cib-4821',
    note: 'Weekly groceries',
    smsBank: 'CIB',
    receipt: {
      merchant: 'Carrefour',
      subtitle: 'Cairo, Egypt · Receipt 4821',
      date: '2026-10-28',
      time: '14:32',
      total: 850,
      footnote: 'Paid by card •4821 · VAT included',
    },
  },
  { id: 'txn-2', title: 'Uber', category: 'transport', date: '2026-10-28', amount: -120, accountId: 'cash' },
  { id: 'txn-3', title: 'Vodafone', category: 'bills', date: '2026-10-28', amount: -250 },
  {
    id: 'txn-4',
    title: 'October salary',
    category: 'salary',
    date: '2026-10-01',
    amount: 30000,
    accountId: 'cib-4821',
    note: 'October salary',
  },
];
