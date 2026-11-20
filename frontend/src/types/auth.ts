export interface AuthUser {
  fullName: string;
  email: string;
}

/** The signed-in user's profile (`GET /users/me`, and `user` in login / refresh / register). */
export interface UserProfile extends AuthUser {
  id: string;
  phone?: string;
  /** ISO 4217, e.g. `EGP`. */
  baseCurrency: string;
  locale: 'en' | 'ar-EG';
  /** IANA zone, e.g. `Africa/Cairo`. */
  timezone: string;
  emailVerified: boolean;
  /** ISO-8601 UTC; left out until the email is verified. */
  emailVerifiedAt?: string;
  /** ISO-8601 UTC. */
  createdAt: string;
}

/** What the server says after it emails a code (sign-up, resend, forgot password). */
export interface CodeDelivery {
  maskedEmail: string;
  codeLength: number;
  expiresInSeconds: number;
  resendAvailableInSeconds: number;
}

export interface SignUpInput {
  fullName: string;
  email: string;
  password: string;
  acceptedTerms: boolean;
}

export interface SignUpResult {
  email: string;
  verification: CodeDelivery;
}

export interface PasswordResetRequest {
  email: string;
  verification: CodeDelivery;
}

/** Short-lived, single-use proof that the reset code was right. Keep it in memory only. */
export interface ResetTokenGrant {
  resetToken: string;
  expiresInSeconds: number;
}

export interface ResetPasswordInput {
  resetToken: string;
  newPassword: string;
  confirmPassword: string;
}
