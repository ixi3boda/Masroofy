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
} as const;
