import { useEffect, useState } from 'react';
import { useIsMounted } from '@/hooks/useIsMounted';
import { useTransactionDraft } from '@/hooks/useTransactionDraft';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { dashboardService } from '@/services/dashboardService';
import { transactionService } from '@/services/transactionService';
import { useTransactionDraftStore } from '@/store/transactionDraftStore';
import { Transaction, TransactionDraft, TransactionDraftErrors, TransactionType } from '@/types/transaction';
import { isApiError } from '@/utils/errors';
import { parseTransactionDraft, toDraftErrors } from '@/utils/transactions';

type Outcome = 'invalid' | 'failed';

/** Field errors the server sent for exactly this draft; editing the draft hides them. */
interface ServerErrors {
  draft: TransactionDraft;
  errors: TransactionDraftErrors;
}

interface TransactionFormOptions {
  type: TransactionType;
  /** Omit to add a new one. */
  transaction?: Transaction;
}

/** The server's field errors as form errors, when every one of them belongs to a form field. */
const serverFieldErrors = (error: unknown, type: TransactionType) =>
  isApiError(error, 'VALIDATION_FAILED') ? toDraftErrors(error.fieldErrors, type) : null;

/** Draft, validation, saving and retry of the Add and Edit forms. */
export const useTransactionForm = ({ type, transaction }: TransactionFormOptions) => {
  const { key, draft, update, changed } = useTransactionDraft(type, transaction);
  const isMounted = useIsMounted();
  const [outcomes, setOutcomes] = useState<Partial<Record<string, Outcome>>>({});
  const [serverErrors, setServerErrors] = useState<Partial<Record<string, ServerErrors>>>({});
  const [saving, setSaving] = useState(false);
  // Bumped when the problem is at the top of the form, so the screen can scroll back up to it.
  const [attention, setAttention] = useState(0);

  useEffect(() => () => useTransactionDraftStore.getState().discardDrafts(), []);

  // A record saved without an account may stay without one.
  const accountRequired = !transaction || !!transaction.accountId;
  const parsed = parseTransactionDraft(draft, type, accountRequired, transactionService.getToday());
  const outcome = outcomes[key];
  const fromServer = serverErrors[key]?.draft === draft ? serverErrors[key]?.errors : undefined;
  const errors: TransactionDraftErrors =
    outcome === 'invalid' ? ('errors' in parsed ? parsed.errors : (fromServer ?? {})) : {};
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
      // The Saved screen reads the month's total synchronously, so refresh it first. Never fails the save.
      await dashboardService.loadSummary().catch(() => undefined);
      return isMounted() ? saved : undefined;
    } catch (error) {
      const fieldErrors = serverFieldErrors(error, type);
      if (fieldErrors) {
        setServerErrors((current) => ({ ...current, [key]: { draft, errors: fieldErrors } }));
        setOutcome('invalid');
        if (fieldErrors.amount) setAttention((count) => count + 1);
      } else {
        setOutcome('failed');
        setAttention((count) => count + 1);
      }
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
    invalid: outcome === 'invalid' && Object.values(errors).some(Boolean),
    failed: outcome === 'failed',
    saving,
    attention,
    submit,
  };
};
