import { useEffect, useState } from 'react';
import { router } from 'expo-router';
import { useIsMounted } from '@/hooks/useIsMounted';
import { useTransactionDraft } from '@/hooks/useTransactionDraft';
import { ROUTES } from '@/navigation/routes';
import { transactionService } from '@/services/transactionService';
import { useTransactionDraftStore } from '@/store/transactionDraftStore';
import { Transaction, TransactionDraftErrors, TransactionType } from '@/types/transaction';
import { parseTransactionDraft } from '@/utils/transactions';

type Outcome = 'invalid' | 'failed';

interface TransactionFormOptions {
  type: TransactionType;
  /** Omit to add a new one. */
  transaction?: Transaction;
}

/** Draft, validation, saving and retry of the Add and Edit forms. */
export const useTransactionForm = ({ type, transaction }: TransactionFormOptions) => {
  const { key, draft, update, changed } = useTransactionDraft(type, transaction);
  const isMounted = useIsMounted();
  const [outcomes, setOutcomes] = useState<Partial<Record<string, Outcome>>>({});
  const [saving, setSaving] = useState(false);
  // Bumped when the problem is at the top of the form, so the screen can scroll back up to it.
  const [attention, setAttention] = useState(0);

  useEffect(() => () => useTransactionDraftStore.getState().discardDrafts(), []);

  // A record saved without an account may stay without one.
  const accountRequired = !transaction || !!transaction.accountId;
  const parsed = parseTransactionDraft(draft, type, accountRequired);
  const outcome = outcomes[key];
  const errors: TransactionDraftErrors = outcome === 'invalid' && 'errors' in parsed ? parsed.errors : {};
  const setOutcome = (value?: Outcome) => setOutcomes((current) => ({ ...current, [key]: value }));

  /** Resolves with the saved record, or with nothing when it wasn't saved or the form was left meanwhile. */
  const submit = async (): Promise<Transaction | undefined> => {
    if ('errors' in parsed) {
      setOutcome('invalid');
      if (parsed.errors.amount) setAttention((count) => count + 1);
      return undefined;
    }
    setOutcome();
    setSaving(true);
    try {
      const saved = transaction
        ? await transactionService.updateTransaction(transaction.id, parsed.input)
        : await transactionService.createTransaction(parsed.input);
      return isMounted() ? saved : undefined;
    } catch {
      setOutcome('failed');
      setAttention((count) => count + 1);
      return undefined;
    } finally {
      setSaving(false);
    }
  };

  const pickCategory = () =>
    router.push({
      pathname: ROUTES.transactions.category,
      params: transaction ? { type, id: transaction.id } : { type },
    });

  return {
    /** Spread onto `TransactionForm`. */
    fields: {
      type,
      draft,
      errors,
      accounts: transactionService.getAccounts().map(({ id, label }) => ({ value: id, title: label })),
      onChange: update,
      onPickCategory: pickCategory,
    },
    changed,
    invalid: outcome === 'invalid' && 'errors' in parsed,
    failed: outcome === 'failed',
    saving,
    attention,
    submit,
  };
};
