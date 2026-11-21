import { mockSmsService } from '@/mocks/services/mockSmsService';
import { SmsService } from './types';

/**
 * Bank SMS import and review. The backend has no SMS API yet, so this is the
 * in-memory mock; swap in an `api` implementation here when it exists — the
 * SMS screens only call this.
 */
export const smsService: SmsService = mockSmsService;
