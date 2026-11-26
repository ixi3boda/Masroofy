/** Currency code shown before every amount. */
export const CURRENCY = 'EGP';

/** Length of every emailed verification / password-reset code. */
export const VERIFICATION_CODE_LENGTH = 6;

/** Seconds before "Resend code" becomes available again, when the server does not say (it uses 60). */
export const RESEND_COOLDOWN_SECONDS = 60;

/** New-password length limits, the same as the backend's PasswordPolicy. */
export const PASSWORD_MIN_LENGTH = 8;
export const PASSWORD_MAX_LENGTH = 128;

/** Name and email parts shorter than this may appear in a password (the backend's MIN_PERSONAL_TOKEN_LENGTH). */
export const PASSWORD_PERSONAL_PART_MIN_LENGTH = 3;
