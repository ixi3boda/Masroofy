import { useState } from 'react';
import { useIsMounted } from '@/hooks/useIsMounted';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { Transaction } from '@/types/transaction';
import { getErrorMessage } from '@/utils/errors';
import { formatExactCurrency } from '@/utils/formatters';
import { getTransactionType } from '@/utils/transactions';

const copy = strings.transactions.deleteDialog;

/** The confirm-then-delete step shared by Transaction Details and Edit Transaction. */
export const useDeleteTransaction = (transaction: Transaction, onDeleted: () => void) => {
  const isMounted = useIsMounted();
  const [visible, setVisible] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>();

  const { id, title, amount, accountId } = transaction;
  const describe = accountId ? copy[getTransactionType(transaction)] : copy.noAccount;

  const ask = () => {
    setError(undefined);
    setVisible(true);
  };

  const dismiss = () => {
    if (!loading) setVisible(false);
  };

  const confirm = async () => {
    setLoading(true);
    try {
      await transactionService.deleteTransaction(id);
      if (!isMounted()) return;
      setVisible(false);
      onDeleted();
    } catch (failure) {
      setError(getErrorMessage(failure));
    } finally {
      setLoading(false);
    }
  };

  return {
    ask,
    /** Spread onto `DeleteTransactionDialog`. */
    dialog: {
      visible,
      loading,
      error,
      message: describe(formatExactCurrency(Math.abs(amount)), title),
      onConfirm: confirm,
      onDismiss: dismiss,
    },
  };
};
