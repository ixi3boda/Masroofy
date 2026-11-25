import { TransactionCategory } from './transaction';

/** purchase = card payment at a merchant · withdrawal = cash withdrawal or transfer (not spending by default). */
export type BankMessageKind = 'purchase' | 'withdrawal';

/** new = waiting for review · reviewed = linked to an existing record · ignored = dismissed by the user. */
export type BankMessageStatus = 'new' | 'reviewed' | 'ignored';

/** An account the app tracks balances for, e.g. "CIB debit •4821" or "Cash". */
export interface TrackingAccount {
  id: string;
  /** Full name for pickers and review fields, e.g. "CIB debit •4821". */
  label: string;
  /** Compact name for record summaries, e.g. "CIB •4821". */
  shortLabel: string;
  /** Last four digits of the linked card, when there is one. */
  cardLast4?: string;
}

/** An existing transaction that has the same amount, merchant, card and day as the message. */
export interface BankMessageMatch {
  transactionId: string;
  merchant: string;
  category: TransactionCategory;
  account: TrackingAccount;
}

/** One bank SMS the user pasted or shared. The source text is read-only. */
export interface BankMessage {
  id: string;
  /** Sender bank, e.g. "CIB". */
  bank: string;
  /** Local Cairo time, `YYYY-MM-DDTHH:mm`. */
  receivedAt: string;
  body: string;
  /** Positive amount in EGP. */
  amount: number;
  kind: BankMessageKind;
  status: BankMessageStatus;
  /** Merchant as written in the SMS, e.g. "CARREFOUR". Withdrawals have none. */
  merchant?: string;
  cardLast4?: string;
  suggestedCategory?: TransactionCategory;
  match?: BankMessageMatch;
  /** When the user linked it (ISO time); set once `status` is `reviewed`. */
  reviewedAt?: string;
}

/** The SMS screens' review routes; which one a message opens is decided by its kind and match. */
export type BankMessageReview = 'match' | 'unmatched' | 'withdrawal';
