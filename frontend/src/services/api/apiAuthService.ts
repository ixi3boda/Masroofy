import * as authApi from '@/api/endpoints/auth';
import {
  clearSession,
  hasStoredSession,
  isSessionOverError,
  refreshSession,
  saveTokens,
  setSessionEndedHandler,
} from '@/api/session';
import { useSessionStore } from '@/store/sessionStore';
import { AuthService } from '../types';

// A refresh rejected anywhere in the app (logout or password reset on another device) signs the user out here.
setSessionEndedHandler(() => useSessionStore.getState().signOut());

/** The real backend behind `AuthService` (used when the auth source is `api`). */
export const apiAuthService: AuthService = {
  async signUp(input) {
    const { user, verification } = await authApi.register(input);
    return { email: user.email, verification };
  },

  async verifySignUpCode(email, code) {
    const { email: verifiedEmail } = await authApi.verifyEmail(email, code);
    return { email: verifiedEmail };
  },

  resendSignUpCode: (email) => authApi.resendVerificationCode(email),

  async logIn(email, password) {
    const tokens = await authApi.login(email, password);
    await saveTokens(tokens);
    return tokens.user;
  },

  async restoreSession() {
    if (!(await hasStoredSession())) return null;
    try {
      return await refreshSession();
    } catch (error) {
      // Session over → no user. Offline / 503 → rethrow, so the caller can offer a retry while the token is kept.
      if (isSessionOverError(error)) return null;
      throw error;
    }
  },

  async logOut() {
    try {
      await authApi.logout();
    } catch {
      // Logging out must never fail for the user: the local session is cleared below either way.
    } finally {
      await clearSession();
    }
  },

  async requestPasswordReset(email) {
    const verification = await authApi.forgotPassword(email);
    return { email: email.trim().toLowerCase(), verification };
  },

  resendResetCode: (email) => authApi.forgotPassword(email),

  verifyResetCode: (email, code) => authApi.verifyResetCode(email, code),

  async resetPassword(input) {
    await authApi.resetPassword(input);
    // The reset ended every session on every device, including this one.
    await clearSession();
  },

  getCurrentUser: () => authApi.getCurrentUser(),
};
