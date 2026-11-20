import { CodeDelivery, ResetPasswordInput, ResetTokenGrant, SignUpInput, UserProfile } from '@/types/auth';
import { request } from '../client';
import { authorizedRequest } from '../session';
import { MessageResponse, RegisterResponse, TokenResponse, VerifyEmailResponse } from '../types';

/**
 * One function per auth endpoint (docs/frontend-api/01…10). Paths are relative to `API_URL`.
 * API 5 (refresh) is in `token.ts`: only `session.ts` calls it, and this file imports `session.ts`.
 */

/** API 1 — `201`. */
export const register = (body: SignUpInput) => request<RegisterResponse>('/auth/register', { body });

/** API 2 — `200`. */
export const verifyEmail = (email: string, code: string) =>
  request<VerifyEmailResponse>('/auth/email-verification/verify', { body: { email, code } });

/** API 3 — `202`. */
export const resendVerificationCode = (email: string) =>
  request<CodeDelivery>('/auth/email-verification/resend', { body: { email } });

/** API 4 — `200`. */
export const login = (email: string, password: string) =>
  request<TokenResponse>('/auth/login', { body: { email, password } });

/** API 6 — `204`. Ends every session on every device. */
export const logout = () => authorizedRequest<void>('/auth/logout');

/** API 7 — `202`. Same answer for unknown emails. */
export const forgotPassword = (email: string) => request<CodeDelivery>('/auth/password/forgot', { body: { email } });

/** API 8 — `200`. */
export const verifyResetCode = (email: string, code: string) =>
  request<ResetTokenGrant>('/auth/password/verify-code', { body: { email, code } });

/** API 9 — `200`. No Bearer token: the reset token is the credential. */
export const resetPassword = (body: ResetPasswordInput) => request<MessageResponse>('/auth/password/reset', { body });

/** API 10 — `200`. */
export const getCurrentUser = () => authorizedRequest<UserProfile>('/users/me', { method: 'GET' });
