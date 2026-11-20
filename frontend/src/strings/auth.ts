import { PASSWORD_MIN_LENGTH } from '@/constants/app';

const previewNotice = 'Static design preview only. No account, sign-in or email action is performed.';

/** Copy for the "01 / Welcome, Authentication & Onboarding" screens. */
export const authStrings = {
  welcome: {
    heading: 'Your money, a little clearer',
    intro: 'Track spending, plan your salary and stay on budget — all in one calm place.',
    regionChip: 'Made for Egypt · Amounts in EGP',
    features: {
      track: {
        title: 'See where every pound goes',
        description: 'Income and expenses together, sorted by category.',
      },
      plan: {
        title: 'Plan your month with confidence',
        description: 'Budgets and salary plans that fit your life.',
      },
      review: {
        title: 'You stay in control',
        description: 'Review every imported SMS or receipt before it’s saved.',
      },
    },
    createAccount: 'Create an account',
    logIn: 'I already have an account',
  },

  signUp: {
    title: 'Create an account',
    heading: 'A fresh start for your finances',
    errorTitle: 'Could not sign up',
    fullNameLabel: 'Full name',
    fullNamePlaceholder: 'Enter your name',
    passwordPlaceholder: 'Create a password',
    passwordHint: `Use at least ${PASSWORD_MIN_LENGTH} characters, including a number and a capital letter.`,
    consentTitle: 'I agree to the Terms & Privacy Policy',
    consentDescription: 'Consent required before creating an account',
    submit: 'Create account',
    haveAccount: 'Already have an account? Log in',
    previewNotice,
  },

  verifyEmail: {
    title: 'Verify signup email',
    heading: 'One step to get started',
    description: 'Confirm your email to finish signing up for Masroofy.',
    codeLabel: 'Six-digit verification code',
    codeHint: 'Enter the code for your new account, not a password-reset code.',
    errorTitle: 'Could not verify',
    submit: 'Verify email',
    previewChip: 'Illustrative preview',
    previewNotice: (code: string) => `No verification email has been sent. Use ${code} in this preview.`,
  },

  login: {
    title: 'Log in',
    heading: 'Welcome back',
    intro: 'Log in to your Masroofy account.',
    errorTitle: 'Could not log in',
    passwordPlaceholder: 'Enter your password',
    forgotPassword: 'Forgot password?',
    submit: 'Log in',
    createAccount: 'Create an account',
    previewNotice: (email: string, password: string) =>
      `Static design preview only. Use ${email} / ${password} in this preview.`,
  },

  forgotPassword: {
    title: 'Forgot password',
    heading: 'Let’s reset your password',
    description: 'Enter the email associated with your account to request a password reset link.',
    emailHint: 'Check the address before continuing.',
    previewTitle: 'Email request preview',
    previewMessage: 'This is a static request screen. No email will be sent.',
    submit: 'Request reset link',
  },

  checkEmail: {
    title: 'Check your email',
    previewChip: 'Confirmation preview',
    heading: 'Check your email',
    description:
      'We have sent a 6-digit password reset code to your email. Enter the code below to reset your password.',
    emailCaption: 'This is the address the request preview is using.',
    nextStepsHeading: 'What to do next',
    nextSteps: [
      'Look in your inbox and spam folder, then follow the reset instructions.',
      'If you entered the wrong address, return to the request screen.',
    ],
    codeLabel: 'Enter 6-digit code',
    errorTitle: 'Could not verify',
    resend: "Didn't receive the email? Resend code",
    submit: 'Verify Code',
    previewTitle: 'No email sent',
    previewMessage: (code: string) =>
      `This design shows the request confirmation only. It has not checked an address or sent a message. Use ${code} in this preview.`,
  },

  resetPassword: {
    title: 'Set new password',
    heading: 'Choose a new password',
    description: 'Use a password you have not used for this account before.',
    newPasswordLabel: 'New password',
    newPasswordPlaceholder: 'Enter a new password',
    confirmLabel: 'Confirm new password',
    confirmPlaceholder: 'Re-enter your new password',
    errorTitle: 'Could not update password',
    requirementsHeading: 'Password requirements',
    requirements: [
      `○ At least ${PASSWORD_MIN_LENGTH} characters`,
      '○ Include at least one number',
      '○ Include at least one capital letter',
      '○ Both passwords must match',
    ],
    submit: 'Update password',
    previewNotice,
  },

  passwordUpdated: {
    title: 'Password updated',
    previewChip: 'Confirmation preview',
    heading: 'Password updated',
    description: 'Your password has been reset successfully.',
    nextHeading: 'Ready to return',
    nextSteps: ['Use your new password the next time you log in.'],
    previewTitle: 'Static confirmation',
    previewMessage: 'No password has been changed. This preview does not authenticate an account.',
    submit: 'Continue to Login',
  },
};
