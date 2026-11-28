import { useCallback, useEffect, useState } from 'react';
import { transactionService } from '@/services/transactionService';
import { getErrorMessage } from '@/utils/errors';

type AccountsState = { status: 'loading' } | { status: 'ready' } | { status: 'failed'; error: string };

const initialState = (): AccountsState =>
  transactionService.getAccounts().length > 0 ? { status: 'ready' } : { status: 'loading' };

/**
 * Loads the accounts a transaction form picks from, so its default account exists when the
 * draft is made. Accounts already known (the mock, or an earlier load) are ready at once and
 * only refreshed in the background.
 */
export const useAccountsLoad = () => {
  const [state, setState] = useState(initialState);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    transactionService.loadAccounts().then(
      () => {
        if (active) setState({ status: 'ready' });
      },
      (error) => {
        if (active) setState((current) => (current.status === 'ready' ? current : { status: 'failed', error: getErrorMessage(error) }));
      }
    );
    return () => {
      active = false;
    };
  }, [attempt]);

  const retry = useCallback(() => {
    setState({ status: 'loading' });
    setAttempt((count) => count + 1);
  }, []);

  return { state, retry };
};
