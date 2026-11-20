import { PASSWORD_MIN_LENGTH } from '@/constants/app';
import { strings } from '@/strings';

const messages = strings.validation;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

export function getEmailError(value: string): string | null {
  if (!value.trim()) return messages.emailRequired;
  if (!isValidEmail(value)) return messages.emailInvalid;
  return null;
}

export function getRequiredError(value: string, label: string): string | null {
  return value.trim() ? null : messages.required(label);
}

/** PASSWORD_MIN_LENGTH+ characters, at least one number, and at least one capital letter. */
export function getNewPasswordError(password: string): string | null {
  if (password.length < PASSWORD_MIN_LENGTH) return messages.passwordTooShort;
  if (!/[0-9]/.test(password)) return messages.passwordNeedsNumber;
  if (!/[A-Z]/.test(password)) return messages.passwordNeedsCapital;
  return null;
}

export function getPasswordMatchError(password: string, confirmPassword: string): string | null {
  return password === confirmPassword ? null : messages.passwordsDoNotMatch;
}
