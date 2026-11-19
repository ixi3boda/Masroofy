const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

export function isValidEmail(value: string): boolean {
  return EMAIL_PATTERN.test(value.trim());
}

export function getEmailError(value: string): string | null {
  if (!value.trim()) return 'Enter your email address.';
  if (!isValidEmail(value)) return 'Enter a valid email address.';
  return null;
}

export function getRequiredError(value: string, label: string): string | null {
  return value.trim() ? null : `Enter your ${label}.`;
}

/** 8+ characters, at least one number, and at least one capital letter. */
export function getNewPasswordError(password: string): string | null {
  if (password.length < 8) return 'Use at least 8 characters.';
  if (!/[0-9]/.test(password)) return 'Include at least one number.';
  if (!/[A-Z]/.test(password)) return 'Include at least one capital letter.';
  return null;
}

export function getPasswordMatchError(password: string, confirmPassword: string): string | null {
  return password === confirmPassword ? null : 'Passwords do not match.';
}
