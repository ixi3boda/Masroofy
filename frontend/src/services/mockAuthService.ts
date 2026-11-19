import { AuthUser } from '@/types/auth';

/**
 * In-memory stand-in for the real auth API so the "01 / Welcome, Authentication
 * & Onboarding" screens can be built and tested end to end before the backend
 * exists. Swap this module out for the real API client once it's ready — every
 * screen only talks to the named exports below, never to the state underneath.
 */

interface StoredUser extends AuthUser {
  password: string;
}

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

const RESPONSE_DELAY_MS = 600;

const users = new Map<string, StoredUser>(
  MOCK_TEST_ACCOUNTS.map((account) => [
    account.email,
    { fullName: account.fullName, email: account.email, password: account.password },
  ])
);

const pendingSignUps = new Map<string, StoredUser>();
const activeResetCodes = new Set<string>();

export class MockAuthError extends Error {}

const wait = (ms = RESPONSE_DELAY_MS) => new Promise((resolve) => setTimeout(resolve, ms));
const normalize = (email: string) => email.trim().toLowerCase();

export const mockAuthService = {
  async signUp(input: { fullName: string; email: string; password: string }): Promise<{ email: string }> {
    await wait();
    const email = normalize(input.email);
    if (users.has(email) || pendingSignUps.has(email)) {
      throw new MockAuthError('An account with this email already exists.');
    }
    pendingSignUps.set(email, { fullName: input.fullName, email, password: input.password });
    return { email };
  },

  async verifySignUpCode(email: string, code: string): Promise<{ email: string }> {
    await wait();
    const key = normalize(email);
    const pending = pendingSignUps.get(key);
    if (!pending) throw new MockAuthError('No pending sign-up found for this email.');
    if (code !== MOCK_VERIFICATION_CODE) {
      throw new MockAuthError(`That code is incorrect. Use ${MOCK_VERIFICATION_CODE} in this preview.`);
    }
    users.set(key, pending);
    pendingSignUps.delete(key);
    return { email: key };
  },

  async resendSignUpCode(_email: string): Promise<void> {
    await wait(300);
  },

  async logIn(email: string, password: string): Promise<AuthUser> {
    await wait();
    const user = users.get(normalize(email));
    if (!user || user.password !== password) {
      throw new MockAuthError('Incorrect email or password.');
    }
    return { email: user.email, fullName: user.fullName };
  },

  async requestPasswordReset(email: string): Promise<{ email: string }> {
    await wait();
    const key = normalize(email);
    // Always "succeeds" so the UI never reveals whether an account exists.
    activeResetCodes.add(key);
    return { email: key };
  },

  async verifyResetCode(email: string, code: string): Promise<{ email: string }> {
    await wait();
    if (code !== MOCK_VERIFICATION_CODE) {
      throw new MockAuthError(`That code is incorrect. Use ${MOCK_VERIFICATION_CODE} in this preview.`);
    }
    return { email: normalize(email) };
  },

  async resendResetCode(_email: string): Promise<void> {
    await wait(300);
  },

  async resetPassword(email: string, newPassword: string): Promise<{ email: string }> {
    await wait();
    const key = normalize(email);
    const user = users.get(key);
    if (user) user.password = newPassword;
    activeResetCodes.delete(key);
    return { email: key };
  },
};
