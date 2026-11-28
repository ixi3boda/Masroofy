import { authorizedRequest } from '../session';
import { CreateTransactionRequest, TransactionResponse } from '../types';

/** API 14 — `201`, or `200` when the same `clientRequestId` was already saved (docs/frontend-api/12-add-transaction.md). */
export const createTransaction = (body: CreateTransactionRequest) =>
  authorizedRequest<TransactionResponse>('/transactions', { method: 'POST', body });
