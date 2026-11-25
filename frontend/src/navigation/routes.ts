import { BankMessageReview } from '@/types/sms';

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
  transactions: {
    list: '/(app)/transactions/list',
    filters: '/(app)/transactions/filters',
    filtered: '/(app)/transactions/filtered',
    search: '/(app)/transactions/search',
    details: '/(app)/transactions/details',
    add: '/(app)/transactions/add',
    category: '/(app)/transactions/category',
    saved: '/(app)/transactions/saved',
    edit: '/(app)/transactions/edit',
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

/** The review screen each kind of bank message opens. */
export const SMS_REVIEW_ROUTES = {
  match: ROUTES.sms.reviewMatch,
  unmatched: ROUTES.sms.reviewUnmatched,
  withdrawal: ROUTES.sms.classifyWithdrawal,
} as const satisfies Record<BankMessageReview, string>;
