import { PASSWORD_MAX_LENGTH, PASSWORD_MIN_LENGTH, PASSWORD_PERSONAL_PART_MIN_LENGTH } from '@/constants/app';
import { strings } from '@/strings';

const messages = strings.validation;
const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
const AMOUNT_PATTERN = /^(\d{1,3}(,\d{3})+|\d+)(\.\d{0,2})?$/;

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

/** The backend's password rules (`fieldErrors[].code` of WEAK_PASSWORD). COMMON_PASSWORD is checked by the server only. */
export type PasswordRule = 'MIN_LENGTH' | 'MAX_LENGTH' | 'NUMBER_OR_SYMBOL' | 'NO_PERSONAL_INFO' | 'COMMON_PASSWORD';

/** What the password must not contain. Either part may be unknown on this screen. */
export interface PasswordPersonalInfo {
  fullName?: string;
  email?: string;
}

/** A number or a symbol: anything except a letter or whitespace. */
const NUMBER_OR_SYMBOL_PATTERN = /[^\p{L}\s]/u;

function personalParts({ fullName, email }: PasswordPersonalInfo): string[] {
  const parts = fullName ? fullName.toLowerCase().split(/\s+/) : [];
  if (email) {
    const lowered = email.trim().toLowerCase();
    const at = lowered.indexOf('@');
    const local = at >= 0 ? lowered.slice(0, at) : lowered;
    parts.push(local, ...local.split(/[._+-]+/));
  }
  return parts.filter((part) => part.length >= PASSWORD_PERSONAL_PART_MIN_LENGTH);
}

/** The rules the password breaks, checked exactly like the backend's PasswordPolicy (except COMMON_PASSWORD). */
export function getBrokenPasswordRules(password: string, personal: PasswordPersonalInfo = {}): PasswordRule[] {
  const broken: PasswordRule[] = [];
  if (password.length < PASSWORD_MIN_LENGTH) broken.push('MIN_LENGTH');
  if (password.length > PASSWORD_MAX_LENGTH) broken.push('MAX_LENGTH');
  if (!NUMBER_OR_SYMBOL_PATTERN.test(password)) broken.push('NUMBER_OR_SYMBOL');
  const lowered = password.toLowerCase();
  if (personalParts(personal).some((part) => lowered.includes(part))) broken.push('NO_PERSONAL_INFO');
  return broken;
}

export function getPasswordMatchError(password: string, confirmPassword: string): string | null {
  return password === confirmPassword ? null : messages.passwordsDoNotMatch;
}

/** "1,250.50" → 1250.5. `null` unless the text is an amount above 0 that can be held to the piastre. */
export function parseAmount(text: string): number | null {
  const amount = text.trim();
  if (!AMOUNT_PATTERN.test(amount)) return null;
  const value = Number(amount.replace(/,/g, ''));
  return value > 0 && Number.isSafeInteger(Math.round(value * 100)) ? value : null;
}
