import { useMemo } from 'react';
import { transactionService } from '@/services/transactionService';
import { useTransactionDraftStore } from '@/store/transactionDraftStore';
import { Transaction, TransactionDraft, TransactionType } from '@/types/transaction';
import { formatDate } from '@/utils/formatters';
import { toTransactionDraft } from '@/utils/transactions';

const emptyDraft = (): TransactionDraft => ({
  amount: '',
  title: '',
  category: null,
  date: formatDate(transactionService.getToday()),
  accountId: transactionService.getAccounts()[0]?.id ?? null,
  note: '',
});

/** The draft of a new `type` entry, or of `transaction` when editing. Expense and income keep separate drafts. */
export const useTransactionDraft = (type: TransactionType, transaction?: Transaction) => {
  const key = transaction?.id ?? type;
  const initial = useMemo(() => (transaction ? toTransactionDraft(transaction) : emptyDraft()), [transaction]);
  const draft = useTransactionDraftStore((state) => state.drafts[key]) ?? initial;

  const update = (changes: Partial<TransactionDraft>) => {
    const { drafts, setDraft } = useTransactionDraftStore.getState();
    setDraft(key, { ...(drafts[key] ?? initial), ...changes });
  };

  const changed = (Object.keys(initial) as (keyof TransactionDraft)[]).some((field) => draft[field] !== initial[field]);

  return { key, draft, update, changed };
};
