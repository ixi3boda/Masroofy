/**
 * Seed data for the mock auth service. QA-only — never shipped as real data.
 */

export interface MockTestAccount {
  /** What this account is useful for, shown nowhere but QA notes/docs. */
  scenario: string;
  fullName: string;
  email: string;
  password: string;
}

/** Seed accounts for manual QA — every one of these already "exists" on load. */
export const MOCK_TEST_ACCOUNTS: MockTestAccount[] = [
  {
    scenario: 'Log in happy path',
    fullName: 'Demo User',
    email: 'demo@masroofy.app',
    password: 'Passw0rd!',
  },
  {
    scenario: 'Sign-up "email already exists" error',
    fullName: 'Taken Account',
    email: 'taken@masroofy.app',
    password: 'Passw0rd!',
  },
  {
    scenario: 'Single-character mailbox name, for maskEmail edge cases',
    fullName: 'A. Fathy',
    email: 'a@masroofy.app',
    password: 'Passw0rd!',
  },
];

/** Code accepted everywhere a 6-digit verification code is asked for. */
export const MOCK_VERIFICATION_CODE = '123456';
