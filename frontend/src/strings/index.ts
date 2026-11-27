import { authStrings } from './auth';
import { categoryStrings } from './categories';
import { commonStrings } from './common';
import { dashboardStrings } from './dashboard';
import { errorStrings } from './errors';
import { smsStrings } from './sms';
import { transactionStrings } from './transactions';
import { validationStrings } from './validation';

/**
 * All user-facing copy, grouped by feature. Screens and components read text
 * from here instead of hard-coding it, so wording changes (or a future Arabic
 * translation) happen in one place.
 */
export const strings = {
  common: commonStrings,
  validation: validationStrings,
  categories: categoryStrings,
  auth: authStrings,
  dashboard: dashboardStrings,
  sms: smsStrings,
  transactions: transactionStrings,
  errors: errorStrings,
};
