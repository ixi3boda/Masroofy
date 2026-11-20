import { PASSWORD_MIN_LENGTH } from '@/constants/app';

/** Form validation messages (see `src/utils/validators.ts`). */
export const validationStrings = {
  emailRequired: 'Enter your email address.',
  emailInvalid: 'Enter a valid email address.',
  required: (fieldName: string) => `Enter your ${fieldName}.`,
  passwordTooShort: `Use at least ${PASSWORD_MIN_LENGTH} characters.`,
  passwordNeedsNumber: 'Include at least one number.',
  passwordNeedsCapital: 'Include at least one capital letter.',
  passwordsDoNotMatch: 'Passwords do not match.',
  fieldNames: {
    fullName: 'full name',
    password: 'password',
  },
};
