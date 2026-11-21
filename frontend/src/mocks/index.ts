/**
 * Everything fake lives under `src/mocks`: seed data in `data/`, in-memory
 * service implementations in `services/`. Screens reach mocks only through
 * `src/services/*`, except for on-screen QA hints (demo login, test code).
 */
export { MOCK_TEST_ACCOUNTS, MOCK_VERIFICATION_CODE } from './data/authAccounts';
export type { MockTestAccount } from './data/authAccounts';
export { mockDashboardSummary } from './data/dashboard';
export { mockBankMessages, mockSharedMessageText, mockTrackingAccounts } from './data/smsMessages';
export { mockAuthService } from './services/mockAuthService';
export { mockSmsService } from './services/mockSmsService';
