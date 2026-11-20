import { PASSWORD_MIN_LENGTH } from '@/constants/app';

/**
 * Text for every backend error `code` (docs/frontend-api/00 §5) and every
 * `fieldErrors[].code`. The server's own `message` is English-only and may
 * change, so the app shows these instead. Unknown codes use `INTERNAL_ERROR`.
 */
export const errorStrings = {
  codes: {
    VALIDATION_FAILED: 'Some fields need your attention.',
    MALFORMED_REQUEST: 'Something went wrong. Try again.',
    WEAK_PASSWORD: 'Choose a stronger password.',
    PASSWORDS_DO_NOT_MATCH: 'Passwords do not match.',
    PASSWORD_REUSED: 'Use a password you have not used for this account before.',
    INVALID_CODE: (remainingAttempts?: number) =>
      remainingAttempts === undefined
        ? 'That code is incorrect.'
        : `That code is incorrect. ${remainingAttempts} ${remainingAttempts === 1 ? 'try' : 'tries'} left.`,
    INVALID_OR_EXPIRED_CODE: 'This code has expired or is no longer valid. Request a new one.',
    INVALID_RESET_TOKEN: 'Your reset session has expired. Start again from “Forgot password”.',
    INVALID_CREDENTIALS: 'Incorrect email or password.',
    INVALID_REFRESH_TOKEN: 'Your session has ended. Log in again.',
    UNAUTHORIZED: 'Your session has ended. Log in again.',
    EMAIL_NOT_VERIFIED: 'Verify your email before logging in.',
    ACCOUNT_DISABLED: 'This account has been disabled.',
    FORBIDDEN: 'You are not allowed to do that.',
    NOT_FOUND: 'Something went wrong. Try again.',
    USER_NOT_FOUND: 'We could not find your account. Log in again.',
    METHOD_NOT_ALLOWED: 'Something went wrong. Try again.',
    EMAIL_ALREADY_IN_USE: 'An account with this email already exists. Log in or reset your password.',
    EMAIL_ALREADY_VERIFIED: 'This email is already verified. You can log in.',
    TOO_MANY_ATTEMPTS: 'Too many incorrect tries. Request a new code.',
    RESEND_COOLDOWN: (retryAfterSeconds?: number) =>
      retryAfterSeconds === undefined
        ? 'Please wait before requesting another code.'
        : `Please wait ${retryAfterSeconds}s before requesting another code.`,
    RATE_LIMITED: 'Too many attempts. Try again later.',
    INTERNAL_ERROR: 'Something went wrong. Try again.',
    EMAIL_DELIVERY_FAILED: 'We could not send the email. Try again.',
    AUTH_PROVIDER_UNAVAILABLE: 'The service is unavailable right now. Try again later.',
    SERVICE_UNAVAILABLE: 'The service is unavailable right now. Try again later.',
    NETWORK_ERROR: 'No connection to Masroofy. Check your internet and try again.',
    TIMEOUT: 'The request took too long. Try again.',
    INVALID_RESPONSE: 'Something went wrong. Try again.',
  },

  fields: {
    NotBlank: 'This field is required.',
    NotNull: 'This field is required.',
    Email: 'Enter a valid email address.',
    Size: 'This is too long.',
    Pattern: 'Enter the code using digits only.',
    AssertTrue: 'You must agree to the Terms & Privacy Policy.',
    MIN_LENGTH: `Use at least ${PASSWORD_MIN_LENGTH} characters.`,
    MAX_LENGTH: 'Use at most 128 characters.',
    NUMBER_OR_SYMBOL: 'Include a number or a symbol.',
    NO_PERSONAL_INFO: 'Do not include your name or email.',
    COMMON_PASSWORD: 'Avoid common or easily guessed passwords.',
    PASSWORDS_MATCH: 'Passwords do not match.',
    PASSWORD_REUSED: 'Use a password you have not used for this account before.',
  } as Record<string, string | undefined>,
};
