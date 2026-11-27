/** `addTransaction` = only the Add Transaction buttons; `transactions` = everything else in the section (list, details…). */
type Feature = 'sms' | 'transactions' | 'addTransaction';

/** Sections whose entry buttons are live. A closed one keeps its buttons visible but unclickable: set `true` to open it. */
const IS_OPEN: Record<Feature, boolean> = {
  sms: true,
  transactions: false,
  addTransaction: true,
};

/** `action` while `feature` is open, otherwise nothing, which makes the control unclickable. */
export const whenOpen = <T>(feature: Feature, action: T): T | undefined => (IS_OPEN[feature] ? action : undefined);
