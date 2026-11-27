import { BankMessage, TrackingAccount } from '@/types/sms';

/** Accounts the user tracks, matching the Home dashboard (CIB account + cash). QA-only. */
export const mockTrackingAccounts: TrackingAccount[] = [
  { id: 'cib-4821', label: 'CIB debit •4821', shortLabel: 'CIB •4821', cardLast4: '4821' },
  { id: 'cash', label: 'Cash', shortLabel: 'Cash' },
];

/**
 * The three bank messages of the "04 / SMS Capture" Figma frames. Their match
 * with an existing transaction is worked out by the mock service, not stored here.
 */
export const mockBankMessages: Omit<BankMessage, 'match'>[] = [
  {
    id: 'sms-cib-1',
    bank: 'CIB',
    receivedAt: '2026-10-28T14:32',
    body: 'Your card ending 4821 was used for EGP 850.00 at CARREFOUR on 28/10/2026 14:32.',
    amount: 850,
    kind: 'purchase',
    status: 'new',
    merchant: 'CARREFOUR',
    cardLast4: '4821',
    suggestedCategory: 'groceries',
  },
  {
    id: 'sms-nbe-1',
    bank: 'NBE',
    receivedAt: '2026-10-27T18:10',
    body: 'Cash withdrawal of EGP 500.00 from card ending 7390 on 27/10/2026 18:10. Please review your transaction.',
    amount: 500,
    kind: 'withdrawal',
    status: 'new',
    cardLast4: '7390',
  },
  {
    id: 'sms-bm-1',
    bank: 'Banque Misr',
    receivedAt: '2026-10-26T09:15',
    body: 'Your card ending 6204 was used for EGP 240.00 at ELECTRICITY on 26/10/2026 09:15.',
    amount: 240,
    kind: 'purchase',
    status: 'new',
    merchant: 'ELECTRICITY',
    cardLast4: '6204',
    suggestedCategory: 'bills',
  },
];

/** What "Share a selected message" receives in mock mode: the next sample, as if shared from Messages. */
export const mockSharedMessageText = mockBankMessages[2].body;
