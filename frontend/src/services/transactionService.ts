import { mockTransactionService } from '@/mocks/services/mockTransactionService';
import { TransactionService } from './types';

/**
 * Transactions: list, add, edit, delete and search history. The backend has no
 * transactions API yet, so this is the in-memory mock; swap in an `api`
 * implementation here when it exists.
 */
export const transactionService: TransactionService = mockTransactionService;
