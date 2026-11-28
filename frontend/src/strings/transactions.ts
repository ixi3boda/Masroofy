import { CURRENCY } from '@/constants/app';

/** Copy for the "03 / Transactions" screens. Notes marked "mock only" are shown only while transactions run on mock data. */
export const transactionStrings = {
  types: { all: 'All', expense: 'Expense', income: 'Income' },
  recorded: 'Recorded',
  account: 'Account',
  category: 'Category',
  allAccounts: 'All accounts',
  clearFilters: 'Clear filters',

  list: {
    title: 'All Transactions',
    tabs: { all: 'All', expense: 'Expenses', income: 'Income' },
    searchLabel: 'Search transactions',
    searchPlaceholder: 'Search merchant or income title',
    /** Mock only. */
    samplePeriod: (month: string) => `${month} · Existing sample entries`,
    /** Mock only. */
    sampleTitle: 'Known sample records',
    sampleMessage:
      'These are the supplied existing entries, not a complete itemisation of October spending. SMS and receipt evidence link to one Carrefour record.',
    sampleFootnote: 'No additional transactions or totals are invented.',
    emptyTitle: 'No transactions here',
    emptyMessage: 'Entries you add appear in this list.',
    filters: 'Filters',
    backToInsights: 'Back to insights',
  },

  filters: {
    title: 'Filter Transactions',
    intro: 'Narrow the existing transaction list. Filters do not change your records or balances.',
    typeHeading: 'Transaction type',
    allCategories: 'All categories',
    otherCategories: (names: string[]) =>
      `Other categories: ${names.slice(0, -1).join(', ')} and ${names[names.length - 1]}.`,
    showCategories: 'Choose another category',
    dateError: 'Enter a date like 28 Oct 2026.',
    rangeError: 'Use a date on or after the From date.',
    apply: 'Apply filters',
  },

  filtered: {
    title: 'Filtered Transactions',
    allTypes: 'All types',
    dateRange: 'Date range',
    applied: (month: string) => `Applied filters · ${month}`,
    appliedRange: (range: string) => `${range} · Applied filters`,
    matching: 'Matching entries',
    /** Mock only. */
    sampleMatching: 'Matching sample entries',
    count: (count: number) => (count === 1 ? '1 result' : `${count} results`),
    view: 'View transaction',
    linkedTitle: 'One record, with linked evidence',
    linkedMessage: (title: string) =>
      `The SMS and receipt belong to this same existing ${title} expense. No duplicate appears in the result.`,
    emptyTitle: 'No matching transactions',
    emptyMessage: 'There are no records for this combination of filters. Try a different type, category or date range.',
    /** Mock only. */
    sampleEmptyMessage:
      'There are no supplied sample records for this combination of filters. Try a different type, category or date range.',
    safeTitle: 'Your records are still here',
    safeMessage: 'Clearing filters returns to the existing list. No transactions have been deleted or changed.',
    edit: 'Edit filters',
  },

  search: {
    title: 'Search',
    placeholder: 'Search merchant, note, or amount...',
    clear: 'CLEAR',
    recent: 'Recent searches',
    /** Mock only. */
    sampleNote: 'Illustrative recent searches using known existing keywords.',
    results: 'Results',
    emptyTitle: 'No matching transactions',
    emptyMessage: 'Try another merchant, note or amount.',
    back: 'BACK TO ALL TRANSACTIONS',
  },

  details: {
    title: 'Transaction Details',
    subtitle: (category: string, type: string) => `${category} · ${type}`,
    included: {
      expense: (month: string) => `Already included in ${month} spending`,
      income: (month: string) => `Already included in ${month} income`,
    },
    dateTime: 'Date & time',
    cairoTime: (time: string) => `${time} Cairo`,
    noAccount: 'Not specified',
    recordedVia: 'Recorded via',
    sources: { sms: 'SMS', manual: 'Manual entry' },
    note: 'Note',
    receiptTitle: 'Attached receipt',
    receiptSummary: (merchant: string, total: string) => `${merchant} · Total ${total}`,
    receiptTotal: `TOTAL · ${CURRENCY}`,
    receiptChip: 'Receipt attached',
    linkedTitle: 'One expense, linked evidence',
    linkedMessage: (bank: string) =>
      `The reviewed ${bank} SMS and receipt belong to this same record. They do not add extra expenses.`,
    edit: 'Edit transaction',
    delete: 'Delete transaction',
    backHome: 'Back to Home',
  },

  form: {
    overline: (month: string) => `Manual entry · ${month}`,
    amount: `Amount · ${CURRENCY}`,
    amountRequired: `Amount · ${CURRENCY} · Required`,
    categoryPlaceholder: 'Choose a category',
    date: 'Date',
    datePlaceholder: 'e.g. 28 Oct 2026',
    accountPlaceholder: 'Select an account',
    notes: 'Notes (optional)',
    retry: 'Retry',
    cancel: 'Cancel',
    /** Mock only. */
    sampleNote: 'Mock data: saved entries update Home and reset when the app reloads.',

    loadingAccounts: 'Loading your accounts',
    accountsFailed: 'Couldn’t load your accounts',

    validation: {
      category: 'Choose a category.',
      date: 'Enter a date like 28 Oct 2026.',
      dateInFuture: 'The date can’t be in the future.',
      account: 'Select an account.',
      otherFields: 'Correct the highlighted fields, then save again. Your other details are still here.',
    },

    expense: {
      screenTitle: 'Add Expense',
      title: 'Merchant',
      titleError: 'Enter the merchant.',
      amountError: `Enter an amount greater than ${CURRENCY} 0`,
      submit: 'Save expense',
      notSaved: 'Expense not saved',
      fixAmount: 'Correct the amount above, then save again. Your other details are still here.',
      saveFailed:
        'This save attempt failed. Your entered details are retained for retry; no additional expense was recorded.',
      unchanged: (month: string, total: string) => `${month} spending stays ${total}. Retry saves this expense once.`,
    },
    income: {
      screenTitle: 'Add Income',
      title: 'Income title',
      titleError: 'Enter the income title.',
      amountError: `Enter a valid amount greater than ${CURRENCY} 0.`,
      submit: 'Save income',
      notSaved: 'Income not saved',
      fixAmount: 'A positive amount is required. Other details are retained; no income has been added.',
      saveFailed:
        'This save attempt failed. Your entered details are retained for retry; no additional income was recorded.',
      unchanged: (month: string, total: string) => `${month} income stays ${total}. Retry saves this income once.`,
    },
  },

  categoryPicker: {
    expense: {
      title: 'Choose Category',
      intro: 'Keep your spending organised. Choose one category for this expense.',
    },
    income: {
      title: 'Income Category',
      intro: 'Choose one category for this income. Your other income details stay as entered.',
    },
    retainedTitle: (title: string) => `${title} retained`,
    existingIncome: (summary: string) => `${summary}. This is the existing income record, not a new deposit.`,
    newIncome: (summary: string) => `${summary}. Nothing is saved until you save the income.`,
    done: 'Done',
    cancel: 'Cancel',
  },

  saved: {
    status: 'Status',
    meta: (category: string, date: string) => `${category} · ${date}`,
    expense: {
      screenTitle: 'Transaction Saved',
      heading: 'Expense recorded',
      description: (title: string, month: string) =>
        `Your ${title} expense is in ${month}’s spending. Everything is up to date.`,
      included: (month: string, total: string) => `Included in ${month} spending of ${total}.`,
      onceTitle: 'One transaction, one record',
      onceMessage: (amount: string, title: string) =>
        `This ${amount} ${title} expense was saved once, with no additional expense.`,
      done: 'Back to Home',
      another: 'Add another',
    },
    income: {
      screenTitle: 'Income Saved',
      heading: 'Income recorded',
      description: (title: string, month: string) => `Your ${title} is included in ${month}’s income.`,
      included: (month: string, total: string) => `${month} income is ${total}.`,
      onceTitle: 'One deposit, one record',
      onceMessage: (amount: string, title: string) =>
        `This ${amount} ${title} income was saved once, with no additional deposit.`,
      done: 'Done',
      another: 'Add Another',
    },
  },

  edit: {
    title: 'Edit Transaction',
    cancel: 'Cancel',
    save: 'Save Changes',
    overline: {
      expense: (title: string) => `${title} · Recorded expense`,
      income: (title: string) => `${title} · Recorded income`,
    },
    note: (title: string) => `Editing the ${title} transaction record.`,
    delete: 'DELETE TRANSACTION',
    failedTitle: 'Changes not saved',
    failedMessage: 'This save attempt failed. Your changes are retained, so you can save again.',
    discardTitle: 'Discard changes?',
    discardMessage: 'You have unsaved changes. Are you sure you want to discard them?',
    discard: 'DISCARD CHANGES',
    keepEditing: 'KEEP EDITING',
  },

  deleteDialog: {
    title: 'Delete Transaction?',
    expense: (amount: string, title: string) =>
      `This will permanently remove this ${amount} expense from your ${title} records and restore your balance. This cannot be undone.`,
    income: (amount: string, title: string) =>
      `This will permanently remove this ${amount} income from your ${title} records and take it out of your balance. This cannot be undone.`,
    noAccount: (amount: string, title: string) =>
      `This will permanently remove this ${amount} record from your ${title} records. No account balance changes. This cannot be undone.`,
    confirm: 'Delete',
    keep: 'KEEP TRANSACTION',
  },
};
