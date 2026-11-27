import { create } from 'zustand';

/** Details the user verified on an unmatched or withdrawal review, shown on the confirmation screen. */
export interface SmsReviewDraft {
  messageId: string;
  /** Merchant, or the withdrawal classification. */
  title: string;
  amount: number;
  /** As typed in the review form, e.g. "26 Oct 2026 · 09:15". */
  dateTime: string;
  /** e.g. "Banque Misr •6204". */
  source: string;
  category: string;
  account: string;
}

interface SmsReviewState {
  draft: SmsReviewDraft | null;
  setDraft: (draft: SmsReviewDraft) => void;
}

/** The in-progress SMS review, between the review form and its confirmation screen. */
export const useSmsReviewStore = create<SmsReviewState>((set) => ({
  draft: null,
  setDraft: (draft) => set({ draft }),
}));
