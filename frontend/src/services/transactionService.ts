import { getDataSource } from '@/config/env';
import { mockTransactionService } from '@/mocks/services/mockTransactionService';
import { apiTransactionService } from './api/apiTransactionService';
import { TransactionService } from './types';

/**
 * Transactions: add, plus list, edit, delete and search history on the mock. The
 * mock or the real backend (APIs 12 and 14), picked by
 * `EXPO_PUBLIC_TRANSACTIONS_SOURCE` (else `EXPO_PUBLIC_API_MODE`, else `mock`).
 * Screens only call this.
 */
export const transactionService: TransactionService =
  getDataSource('transactions') === 'api' ? apiTransactionService : mockTransactionService;
