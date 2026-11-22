export type TransactionType = 'expense' | 'income';

export type ExpenseCategory = 'groceries' | 'transport' | 'bills' | 'rent' | 'dining' | 'health' | 'shopping' | 'other';
export type IncomeCategory = 'salary' | 'freelance' | 'investment' | 'gift' | 'refund' | 'otherIncome';
export type TransactionCategory = ExpenseCategory | IncomeCategory;

/** A receipt as captured. It is evidence, so editing the transaction never changes it. */
export interface TransactionReceipt {
  merchant: string;
  /** e.g. "Cairo, Egypt · Receipt 4821" */
  subtitle: string;
  /** ISO calendar date, `YYYY-MM-DD`. */
  date: string;
  /** `HH:mm`, as printed. */
  time: string;
  total: number;
  /** e.g. "Paid by card •4821 · VAT included" */
  footnote: string;
}

export interface Transaction {
  id: string;
  /** Merchant of an expense, or the title of an income. */
  title: string;
  category: TransactionCategory;
  /** ISO calendar date, `YYYY-MM-DD`. */
  date: string;
  /** `HH:mm` in Cairo, when known. */
  time?: string;
  /** Signed amount in EGP: negative for expenses, positive for income. */
  amount: number;
  /** Missing when the record was saved without an account. */
  accountId?: string;
  note?: string;
  /** Set when the record is linked to a bank SMS, e.g. "CIB". */
  smsBank?: string;
  receipt?: TransactionReceipt;
}

/** The fields a user can set when adding or editing. */
export type TransactionInput = Pick<Transaction, 'title' | 'category' | 'date' | 'amount' | 'accountId' | 'note'>;

/** A transaction form exactly as typed, before validation. */
export interface TransactionDraft {
  amount: string;
  title: string;
  category: TransactionCategory | null;
  /** e.g. "28 Oct 2026" */
  date: string;
  accountId: string | null;
  note: string;
}

export type TransactionDraftErrors = Partial<Record<keyof TransactionDraft, string>>;

export type TransactionTypeFilter = 'all' | TransactionType;

export interface TransactionFilters {
  /** ISO calendar dates, both inclusive. */
  from: string;
  to: string;
  type: TransactionTypeFilter;
  category: 'all' | TransactionCategory;
  /** An account id, or `all`. */
  accountId: string;
}
