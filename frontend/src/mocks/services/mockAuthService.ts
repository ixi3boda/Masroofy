import { AuthUser } from '@/types/auth';
import { AppError } from '@/utils/errors';
import { MOCK_TEST_ACCOUNTS, MOCK_VERIFICATION_CODE } from '@/mocks/data/authAccounts';

/**
 * In-memory stand-in for the auth backend so the "01 / Welcome, Authentication
 * & Onboarding" screens can be tested end to end. Screens never import this
 * file directly — they use `@/services/authService`, which points here today.
 */

interface StoredUser extends AuthUser {
  password: string;
}

const RESPONSE_DELAY_MS = 600;

const users = new Map<string, StoredUser>(
  MOCK_TEST_ACCOUNTS.map((account) => [
    account.email,
    { fullName: account.fullName, email: account.email, password: account.password },
  ])
);

const pendingSignUps = new Map<string, StoredUser>();
const activeResetCodes = new Set<string>();

const wait = (ms = RESPONSE_DELAY_MS) => new Promise((resolve) => setTimeout(resolve, ms));
const normalize = (email: string) => email.trim().toLowerCase();
const wrongCode = () =>
  new AppError(`That code is incorrect. Use ${MOCK_VERIFICATION_CODE} in this preview.`);

export const mockAuthService = {
  async signUp(input: { fullName: string; email: string; password: string }): Promise<{ email: string }> {
    await wait();
    const email = normalize(input.email);
    if (users.has(email) || pendingSignUps.has(email)) {
      throw new AppError('An account with this email already exists.');
    }
    pendingSignUps.set(email, { fullName: input.fullName, email, password: input.password });
    return { email };
  },

  async verifySignUpCode(email: string, code: string): Promise<AuthUser> {
    await wait();
    const key = normalize(email);
    const pending = pendingSignUps.get(key);
    if (!pending) throw new AppError('No pending sign-up found for this email.');
    if (code !== MOCK_VERIFICATION_CODE) throw wrongCode();
    users.set(key, pending);
    pendingSignUps.delete(key);
    return { email: key, fullName: pending.fullName };
  },

  async resendSignUpCode(_email: string): Promise<void> {
    await wait(300);
  },

  async logIn(email: string, password: string): Promise<AuthUser> {
    await wait();
    const user = users.get(normalize(email));
    if (!user || user.password !== password) {
      throw new AppError('Incorrect email or password.');
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
    if (code !== MOCK_VERIFICATION_CODE) throw wrongCode();
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
