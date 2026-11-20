import { CURRENCY, RESEND_COOLDOWN_SECONDS, VERIFICATION_CODE_LENGTH } from '@/constants/app';
import { CodeDelivery, UserProfile } from '@/types/auth';
import { AuthService } from '@/services/types';
import { ApiError } from '@/utils/errors';
import { maskEmail } from '@/utils/maskEmail';
import { MOCK_TEST_ACCOUNTS, MOCK_VERIFICATION_CODE } from '@/mocks/data/authAccounts';

/**
 * In-memory stand-in for the auth backend, following the same contract as the
 * real API (docs/frontend-api/01…10): same shapes, same error codes, 5 tries per
 * code, a resend cooldown, a single-use reset token. Every code is
 * `MOCK_VERIFICATION_CODE`. Screens never import this file: they use
 * `@/services/authService`, which picks it when the auth source is `mock`.
 */

interface StoredUser {
  profile: UserProfile;
  password: string;
}

interface ActiveCode {
  failedAttempts: number;
  expiresAt: number;
}

const RESPONSE_DELAY_MS = 600;
const CODE_LIFETIME_SECONDS = 600;
const RESET_TOKEN_LIFETIME_SECONDS = 900;
const MAX_CODE_ATTEMPTS = 5;

const wait = (ms = RESPONSE_DELAY_MS) => new Promise((resolve) => setTimeout(resolve, ms));
const normalize = (email: string) => email.trim().toLowerCase();
const now = () => Date.now();

const createProfile = (fullName: string, email: string, verified: boolean): UserProfile => {
  const timestamp = new Date().toISOString();
  return {
    id: `mock-${Math.random().toString(36).slice(2, 10)}`,
    fullName: fullName.trim(),
    email,
    baseCurrency: CURRENCY,
    locale: 'en',
    timezone: 'Africa/Cairo',
    emailVerified: verified,
    ...(verified ? { emailVerifiedAt: timestamp } : {}),
    createdAt: timestamp,
  };
};

const users = new Map<string, StoredUser>(
  MOCK_TEST_ACCOUNTS.map((account) => [
    account.email,
    { profile: createProfile(account.fullName, account.email, true), password: account.password },
  ])
);

/** Keys are `verify:<email>` or `reset:<email>`; the two kinds of code never mix. */
const activeCodes = new Map<string, ActiveCode>();
const lastSentAt = new Map<string, number>();
const resetTokens = new Map<string, { email: string; expiresAt: number }>();
let signedInEmail: string | null = null;

const delivery = (email: string): CodeDelivery => ({
  maskedEmail: maskEmail(email),
  codeLength: VERIFICATION_CODE_LENGTH,
  expiresInSeconds: CODE_LIFETIME_SECONDS,
  resendAvailableInSeconds: RESEND_COOLDOWN_SECONDS,
});

/** The resend timer runs per email and kind of code, for unknown emails too (no account leak). */
const startCooldown = (key: string) => {
  const sentAt = lastSentAt.get(key);
  const elapsedSeconds = sentAt === undefined ? Infinity : (now() - sentAt) / 1000;
  if (elapsedSeconds < RESEND_COOLDOWN_SECONDS) {
    const retryAfterSeconds = Math.ceil(RESEND_COOLDOWN_SECONDS - elapsedSeconds);
    throw new ApiError('RESEND_COOLDOWN', 429, undefined, [], { retryAfterSeconds });
  }
  lastSentAt.set(key, now());
};

const issueCode = (key: string) => {
  activeCodes.set(key, { failedAttempts: 0, expiresAt: now() + CODE_LIFETIME_SECONDS * 1000 });
};

const checkCode = (key: string, code: string) => {
  const active = activeCodes.get(key);
  if (!active || active.expiresAt < now()) {
    activeCodes.delete(key);
    throw new ApiError('INVALID_OR_EXPIRED_CODE', 400);
  }
  if (code === MOCK_VERIFICATION_CODE) {
    activeCodes.delete(key);
    return;
  }
  active.failedAttempts += 1;
  if (active.failedAttempts >= MAX_CODE_ATTEMPTS) {
    activeCodes.delete(key);
    throw new ApiError('TOO_MANY_ATTEMPTS', 429);
  }
  throw new ApiError('INVALID_CODE', 400, undefined, [], {
    remainingAttempts: MAX_CODE_ATTEMPTS - active.failedAttempts,
  });
};

const sendResetCode = (email: string): CodeDelivery => {
  const key = `reset:${email}`;
  startCooldown(key);
  if (users.has(email)) issueCode(key);
  return delivery(email);
};

const markVerified = (user: StoredUser) => {
  if (user.profile.emailVerified) return;
  user.profile = { ...user.profile, emailVerified: true, emailVerifiedAt: new Date().toISOString() };
};

export const mockAuthService: AuthService = {
  async signUp(input) {
    await wait();
    const email = normalize(input.email);
    if (!input.acceptedTerms) {
      throw new ApiError('VALIDATION_FAILED', 400, undefined, [{ field: 'acceptedTerms', code: 'AssertTrue' }]);
    }
    if (users.has(email)) throw new ApiError('EMAIL_ALREADY_IN_USE', 409);
    users.set(email, { profile: createProfile(input.fullName, email, false), password: input.password });
    lastSentAt.set(`verify:${email}`, now());
    issueCode(`verify:${email}`);
    return { email, verification: delivery(email) };
  },

  async verifySignUpCode(email, code) {
    await wait();
    const key = normalize(email);
    const user = users.get(key);
    if (user?.profile.emailVerified) throw new ApiError('EMAIL_ALREADY_VERIFIED', 409);
    checkCode(`verify:${key}`, code);
    if (user) markVerified(user);
    return { email: key };
  },

  async resendSignUpCode(email) {
    await wait(300);
    const key = normalize(email);
    startCooldown(`verify:${key}`);
    const user = users.get(key);
    if (user && !user.profile.emailVerified) issueCode(`verify:${key}`);
    return delivery(key);
  },

  async logIn(email, password) {
    await wait();
    const key = normalize(email);
    const user = users.get(key);
    if (!user || user.password !== password) throw new ApiError('INVALID_CREDENTIALS', 401);
    if (!user.profile.emailVerified) {
      throw new ApiError('EMAIL_NOT_VERIFIED', 403, undefined, [], { maskedEmail: maskEmail(key) });
    }
    signedInEmail = key;
    return user.profile;
  },

  async restoreSession() {
    // Nothing survives an app restart in the mock, so there is never a stored session.
    return null;
  },

  async logOut() {
    await wait(300);
    signedInEmail = null;
  },

  async requestPasswordReset(email) {
    await wait();
    const key = normalize(email);
    return { email: key, verification: sendResetCode(key) };
  },

  async resendResetCode(email) {
    await wait(300);
    return sendResetCode(normalize(email));
  },

  async verifyResetCode(email, code) {
    await wait();
    const key = normalize(email);
    checkCode(`reset:${key}`, code);
    const resetToken = `mock-reset-${Math.random().toString(36).slice(2)}`;
    resetTokens.set(resetToken, { email: key, expiresAt: now() + RESET_TOKEN_LIFETIME_SECONDS * 1000 });
    return { resetToken, expiresInSeconds: RESET_TOKEN_LIFETIME_SECONDS };
  },

  async resetPassword({ resetToken, newPassword, confirmPassword }) {
    await wait();
    if (newPassword !== confirmPassword) {
      throw new ApiError('PASSWORDS_DO_NOT_MATCH', 400, undefined, [
        { field: 'confirmPassword', code: 'PASSWORDS_MATCH' },
      ]);
    }
    const grant = resetTokens.get(resetToken);
    const user = grant && grant.expiresAt >= now() ? users.get(grant.email) : undefined;
    if (!grant || !user) throw new ApiError('INVALID_RESET_TOKEN', 400);
    if (user.password === newPassword) {
      throw new ApiError('PASSWORD_REUSED', 400, undefined, [{ field: 'newPassword', code: 'PASSWORD_REUSED' }]);
    }
    resetTokens.delete(resetToken);
    user.password = newPassword;
    markVerified(user);
    if (signedInEmail === grant.email) signedInEmail = null;
  },

  async getCurrentUser() {
    await wait(300);
    const user = signedInEmail ? users.get(signedInEmail) : undefined;
    if (!user) throw new ApiError('UNAUTHORIZED', 401);
    return user.profile;
  },
};
