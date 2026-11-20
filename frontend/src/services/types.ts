import {
  CodeDelivery,
  PasswordResetRequest,
  ResetPasswordInput,
  ResetTokenGrant,
  SignUpInput,
  SignUpResult,
  UserProfile,
} from '@/types/auth';

/**
 * The auth contract every implementation follows (mock and API), so screens
 * behave the same whichever source `EXPO_PUBLIC_AUTH_SOURCE` picks. Failures
 * throw `ApiError` with the backend's `code` (docs/frontend-api/01…10).
 */
export interface AuthService {
  /** API 1. The user is not signed in afterwards: they verify the email, then log in. */
  signUp(input: SignUpInput): Promise<SignUpResult>;
  /** API 2. No tokens: the next step is Login. */
  verifySignUpCode(email: string, code: string): Promise<{ email: string }>;
  /** API 3. */
  resendSignUpCode(email: string): Promise<CodeDelivery>;
  /** API 4. Keeps the tokens internally and returns the profile. */
  logIn(email: string, password: string): Promise<UserProfile>;
  /** API 5 at app start: the stored session's profile, or `null` when there is none or it is over. */
  restoreSession(): Promise<UserProfile | null>;
  /** API 6. Never throws; always clears the local session. */
  logOut(): Promise<void>;
  /** API 7. */
  requestPasswordReset(email: string): Promise<PasswordResetRequest>;
  /** API 7, from the "Resend" button on the reset-code screen. */
  resendResetCode(email: string): Promise<CodeDelivery>;
  /** API 8. */
  verifyResetCode(email: string, code: string): Promise<ResetTokenGrant>;
  /** API 9. Ends every session; the user logs in again. */
  resetPassword(input: ResetPasswordInput): Promise<void>;
  /** API 10. */
  getCurrentUser(): Promise<UserProfile>;
}
