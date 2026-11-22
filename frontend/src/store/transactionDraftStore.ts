import { create } from 'zustand';
import { TransactionDraft } from '@/types/transaction';

interface TransactionDraftState {
  /** Keyed by the edited transaction's id, or by type when adding. */
  drafts: Partial<Record<string, TransactionDraft>>;
  setDraft: (key: string, draft: TransactionDraft) => void;
  discardDrafts: () => void;
}

/** What is typed in the add / edit form, shared with the category picker pushed on top of it. */
export const useTransactionDraftStore = create<TransactionDraftState>((set) => ({
  drafts: {},
  setDraft: (key, draft) => set((state) => ({ drafts: { ...state.drafts, [key]: draft } })),
  discardDrafts: () => set({ drafts: {} }),
}));
