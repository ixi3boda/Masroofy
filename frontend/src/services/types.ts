import {
  CodeDelivery,
  PasswordResetRequest,
  ResetPasswordInput,
  ResetTokenGrant,
  SignUpInput,
  SignUpResult,
  UserProfile,
} from '@/types/auth';
import { BankMessage, BankMessageReview, TrackingAccount } from '@/types/sms';

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

/**
 * Bank SMS import and review (Figma "04 / SMS Capture"). Reads are synchronous
 * like `dashboardService`; actions are async. Only a mock exists today.
 */
export interface SmsService {
  /** Every imported message, latest import first, whatever its status. */
  getMessages(): BankMessage[];
  getMessage(id: string): BankMessage | undefined;
  /** Accounts a message can be recorded against. */
  getTrackingAccounts(): TrackingAccount[];
  /** Text received from the system share sheet ("Share a selected message"). */
  getSharedText(): string;
  /** `null` when the text is empty or has no amount and date. The same text again returns the existing message. */
  importMessage(text: string): Promise<BankMessage | null>;
  /** Reads amount, merchant and date, then says which review the message needs. */
  extractDetails(id: string): Promise<BankMessageReview>;
  /** Links the message to its matching transaction; no new expense is added. */
  confirmMatch(id: string): Promise<BankMessage>;
  /** Hides the message from both lists without recording anything. */
  ignoreMessage(id: string): Promise<void>;
}
