type Feature = 'sms' | 'transactions';

/** Sections whose entry buttons are live. A closed one keeps its buttons visible but unclickable: set `true` to open it. */
const IS_OPEN: Record<Feature, boolean> = {
  sms: false,
  transactions: false,
};

/** `action` while `feature` is open, otherwise nothing, which makes the control unclickable. */
export const whenOpen = <T>(feature: Feature, action: T): T | undefined => (IS_OPEN[feature] ? action : undefined);
