/**
 * Every route path in one place, so screens never hard-code URLs.
 * Keep in sync with the files under `src/app/`.
 */
export const ROUTES = {
  auth: {
    welcome: '/(auth)/welcome',
    signUp: '/(auth)/sign-up',
    verifyEmail: '/(auth)/verify-email',
    login: '/(auth)/login',
    forgotPassword: '/(auth)/forgot-password',
    checkEmail: '/(auth)/check-email',
    resetPassword: '/(auth)/reset-password',
    passwordUpdated: '/(auth)/password-updated',
  },
  app: {
    home: '/(app)/home',
  },
  sms: {
    messages: '/(app)/sms/messages',
    import: '/(app)/sms/import',
    importFailed: '/(app)/sms/import-failed',
    processing: '/(app)/sms/processing',
    reviewMatch: '/(app)/sms/review-match',
    reviewUnmatched: '/(app)/sms/review-unmatched',
    classifyWithdrawal: '/(app)/sms/classify-withdrawal',
    matchConfirmed: '/(app)/sms/match-confirmed',
    reviewedPreview: '/(app)/sms/reviewed-preview',
  },
} as const;
