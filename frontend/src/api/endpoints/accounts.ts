import { authorizedRequest } from '../session';
import { AccountResponse } from '../types';

/** API 12 — `200`. The user's open accounts, oldest first (docs/frontend-api/12-add-transaction.md). */
export const getAccounts = () => authorizedRequest<AccountResponse[]>('/accounts', { method: 'GET' });
