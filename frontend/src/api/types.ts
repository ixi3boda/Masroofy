import { CodeDelivery, UserProfile } from '@/types/auth';
import { ApiErrorDetails, FieldError } from '@/utils/errors';

/** Request and response bodies, as in docs/frontend-api/01…10. */

/** The error body every endpoint uses (docs/frontend-api/00 §5). */
export interface ApiErrorBody {
  timestamp?: string;
  status?: number;
  code?: string;
  message?: string;
  path?: string;
  fieldErrors?: FieldError[];
  details?: ApiErrorDetails;
}

/** Login (API 4) and refresh (API 5). */
export interface TokenResponse {
  accessToken: string;
  refreshToken: string;
  tokenType: 'Bearer';
  /** Access token lifetime in seconds. */
  expiresIn: number;
  user: UserProfile;
}

/** Register (API 1), `201`. */
export interface RegisterResponse {
  user: UserProfile;
  verification: CodeDelivery;
  verificationEmailSent: boolean;
}

/** Verify email (API 2), `200`. */
export interface VerifyEmailResponse {
  email: string;
  emailVerified: boolean;
}

/** Reset password (API 9), `200`. */
export interface MessageResponse {
  message: string;
}
