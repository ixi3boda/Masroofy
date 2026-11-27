import { CURRENCY } from '@/constants/app';

/** Copy for the "04 / SMS Capture" screens. Notes marked "mock only" are shown only while SMS runs on mock data. */
export const smsStrings = {
  messages: {
    title: 'Bank Messages',
    guidanceTitle: 'Import selected bank messages',
    guidanceMessage:
      'Paste or share only the bank messages you choose. Review every extraction before saving; Masroofy does not access your iOS inbox.',
    importButton: 'Import a bank SMS',
    tabNew: (count: number) => `New · ${count}`,
    tabReviewed: (count: number) => `Reviewed · ${count}`,
    listCaption: 'IMPORTED SAMPLES · SOURCE TEXT IS READ-ONLY',
    newChip: 'New',
    reviewMessage: 'Review message',
    duplicateTitle: 'Possible duplicate',
    duplicateMessage: (merchant: string) =>
      `Matches the recorded ${merchant} expense. Review to link it, not add it again.`,
    newFootnote: (banks: string) =>
      `Imported messages are not expenses until reviewed. ${banks} samples are not included in your balances.`,
    emptyNewTitle: 'No new messages',
    emptyNewMessage: 'Import a bank SMS to review it here.',

    reviewedTitle: (bank: string) => `${bank} message reviewed`,
    reviewedMessage: (merchant: string) => `Linked to the same ${merchant} record. No duplicate was added.`,
    reviewedChip: 'Reviewed · Linked',
    reviewedRowTitle: (bank: string, merchant: string) => `${bank} · ${merchant}`,
    reviewedMeta: (category: string, account: string) => `Existing expense · ${category} · ${account}`,
    viewTransaction: 'View existing transaction',
    stillNew: (count: number) => `Still new · ${count}`,
    statusMatch: 'New · Possible duplicate',
    statusWithdrawal: 'New · Classify withdrawal',
    statusUnmatched: 'New · Review required',
    metaMatch: (merchant: string) => `Matches the recorded ${merchant} expense`,
    metaWithdrawal: 'Not recorded · Verify movement and accounts',
    metaUnmatched: (merchant: string) => `${merchant} · Account and category unverified`,
    reviewedFootnote: (month: string, spending: string, balance: string) =>
      `New samples remain outside the baseline. ${month} spending stays ${spending} and tracked balance stays ${balance}.`,
    emptyReviewedTitle: 'No reviewed messages yet',
    emptyReviewedMessage: 'Messages you confirm as already recorded appear here.',
  },

  import: {
    title: 'Import Bank SMS',
    guidanceTitle: 'Only the message you choose',
    guidanceMessage:
      'On iOS, copy and paste a bank SMS or share selected text manually. Masroofy does not request inbox permission or read your messages automatically.',
    pasteHeading: 'Paste a bank message',
    fieldLabel: 'Selected message text',
    fieldPlaceholder: 'Paste your selected bank SMS here',
    fieldHint: 'Remove any unrelated personal information before review.',
    consentTitle: 'I consent to reviewing this selected text',
    consentDescription: 'Required for this message only; not inbox access',
    consentRequired: 'Tick the consent box to review this message.',
    howHeading: 'How manual import works',
    howSteps: [
      '1. Select a bank message in Messages.',
      '2. Copy its text, then paste it here, or use the share option.',
      '3. Check the extracted fields before any save.',
    ],
    /** Mock only. */
    previewNote: 'Static import controls only. Nothing is read, imported or saved in this preview.',
    submit: 'Review selected message',
    share: 'Share a selected message',
    cancel: 'Cancel',
  },

  importFailed: {
    title: 'Import Bank SMS',
    heading: 'No message to review',
    description: 'The selected text is empty or could not be read. Nothing has been imported.',
    tryHeading: 'Try another way',
    tryMessage: 'Copy the complete bank message, including its amount and date, then paste it again.',
    fieldLabel: 'Selected message',
    fieldPlaceholder: 'Paste bank message text',
    fieldHint: 'Share only the message you want to review. Do not share PINs or verification codes.',
    fieldError: 'This text has no amount and date. Paste the complete bank message.',
    bannerTitle: 'No financial changes',
    bannerMessage: 'No expenses, transfers or income were created. Masroofy has no automatic iOS inbox access.',
    submit: 'Paste a message',
    share: 'Share selected text',
    cancel: 'Cancel',
  },

  processing: {
    title: 'Reviewing Message',
    /** Mock only. */
    previewChip: 'Processing preview · Simulated',
    heading: 'Finding transaction details',
    description: 'A preview of extracting the amount, merchant and date from one selected message.',
    source: 'Selected source',
    steps: [
      { label: 'Read selected text', status: 'Preview' },
      { label: 'Extract fields', status: 'In progress' },
      { label: 'Verify account & category', status: 'Next' },
    ],
    /** Mock only. */
    bannerTitle: 'Nothing recorded',
    bannerMessage:
      'No actual detection runs in this preview. Review and confirm all fields in the app before saving. Balances are unchanged.',
    cancel: 'Cancel review',
  },

  review: {
    title: 'Review Bank SMS',
    originalTitle: (bank: string) => `Original message · ${bank}`,
    originalSubtitle: (dateTime: string) => `${dateTime} · Read-only`,
    detailsHeading: 'Check extracted details',
    /** How a message's source is named when no account is mapped to it, e.g. "card •6204". */
    cardSource: (card: string) => `card •${card}`,
    cancel: 'Cancel',
    errors: {
      amount: 'Enter an amount greater than 0.',
      required: 'This field is required.',
      category: 'Select a category.',
      account: 'Select the account to record this against.',
    },

    match: {
      confidenceChip: 'High confidence · Review required',
      bannerTitle: (merchant: string, amount: string) => `Already recorded: ${merchant} · ${amount}`,
      bannerMessage:
        'Same amount, merchant, card and time as your existing transaction. Confirm will match this SMS. No duplicate expense will be added.',
      amountLabel: `Amount · ${CURRENCY}`,
      merchantLabel: 'Merchant',
      dateLabel: 'Date & time',
      categoryLabel: 'Category · Suggested',
      accountLabel: 'Account',
      footnote: 'Only this selected bank message is being reviewed. You stay in control of what is kept.',
      confirm: 'Confirm match',
      ignore: 'Ignore message',
    },

    unmatched: {
      statusChip: 'Separate branch · Not yet recorded',
      bannerTitle: 'No existing match selected',
      bannerMessage: (amount: string, source: string, accounts: string) =>
        `This ${amount} sample is not in the baseline. Verify the category and tracking account yourself; ${source} is not mapped to ${accounts}.`,
      accountsOr: (accounts: string[]) => accounts.join(' or '),
      amountLabel: `Amount · ${CURRENCY} · Required`,
      merchantLabel: 'Merchant · Required',
      dateLabel: 'Date & time · Cairo · Required',
      categoryLabel: 'Category · Verify suggestion',
      categoryNeedsConfirmation: (category: string) => `${category} · Requires confirmation`,
      categoryPlaceholder: 'Select a category',
      accountLabel: 'Tracking account · Required',
      accountPlaceholder: 'Select and verify an account',
      checkDetails: 'I verified the amount, date and category',
      checkAccount: 'I verified the tracking account',
      checksRequired: 'Tick both checks to confirm you verified the details.',
      /** Mock only. */
      footnote:
        'Static review preview. User-confirmed details are required before a real save. No account is inferred and no totals change.',
      submit: 'Review verified details',
    },

    withdrawal: {
      title: 'Classify Withdrawal',
      statusChip: 'Unrecorded source · Action required',
      bannerTitle: 'A withdrawal is not spending by default',
      bannerMessage:
        'Moving money to cash or between accounts must not be counted again as an expense. Choose what happened first.',
      options: {
        cashWithdrawal: { title: 'Cash withdrawal / transfer', description: 'Money moved between your own funds' },
        otherTransfer: { title: 'Other transfer', description: 'Clarify the movement before recording' },
        needsClarification: { title: 'Needs clarification', description: 'Keep this message unrecorded' },
      },
      classificationRequired: 'Choose what happened first.',
      amountLabel: `Amount · ${CURRENCY}`,
      sourceLabel: 'Source tracking account · Required',
      sourcePlaceholder: (source: string) => `Verify account for ${source}`,
      destinationLabel: 'Destination · Required for transfer',
      destinationPlaceholder: 'Select and verify destination',
      transferAccounts: (source: string, destination: string) => `${source} → ${destination}`,
      footnote: (bank: string) =>
        `No classification or account is selected. Do not assume ${bank} maps to CIB. Confirm both sides and check for existing records before a real transfer; baseline balances remain unchanged.`,
      submit: 'Review classification',
      leave: 'Leave unrecorded',
    },
  },

  matchConfirmed: {
    title: 'SMS Confirmed',
    heading: 'Matched to existing transaction',
    description: (bank: string, merchant: string) =>
      `Your ${bank} message has been reviewed and linked to the ${merchant} record.`,
    chip: 'No duplicate added',
    recordMeta: (category: string, date: string) => `${category} · ${date}`,
    account: 'Account',
    status: 'Status',
    recorded: 'Recorded',
    footnote: (month: string, spending: string) => `Included in ${month} spending of ${spending}.`,
    bannerTitle: (month: string, spending: string) => `${month} spending stays ${spending}`,
    bannerMessage: (amount: string) =>
      `The ${amount} expense was already included. This confirmation does not change your balance.`,
    viewDetails: 'View details',
    backHome: 'Back to Home',
  },

  reviewedPreview: {
    title: 'SMS Confirmation',
    /** Mock only. */
    previewChip: 'SAMPLE BRANCH PREVIEW',
    heading: 'Reviewed transaction preview',
    description:
      'A separate example of the confirmation after user-verified details, not a change to your current records.',
    dateTime: (dateTime: string) => `${dateTime} Cairo`,
    source: 'Source',
    sourceValue: (bank: string, card: string) => `${bank} •${card}`,
    category: 'Category',
    account: 'Tracking account',
    notSavedChip: 'Not saved to the baseline',
    bannerTitle: 'Verification before real save',
    bannerMessage:
      'The app must require confirmation of the amount, date, category and tracking account. No account mapping or updated balance is assumed in this template.',
    /** Mock only. */
    footnote: (month: string) => `Static confirmation preview only. ${month} totals and balances remain unchanged.`,
    backToMessages: 'Back to messages',
    reviewDetails: 'Review details',
  },
};
