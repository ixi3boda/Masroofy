/** Form validation messages (see `src/utils/validators.ts`). */
export const validationStrings = {
  emailRequired: 'Enter your email address.',
  emailInvalid: 'Enter a valid email address.',
  required: (fieldName: string) => `Enter your ${fieldName}.`,
  passwordRequirementsNotMet: 'Your password does not meet every requirement.',
  passwordsDoNotMatch: 'Passwords do not match.',
  fieldNames: {
    fullName: 'full name',
    password: 'password',
  },
};
