import { create } from 'zustand';
import { TransactionFilters } from '@/types/transaction';

interface TransactionFilterState {
  /** `null` until filters are applied, and after they are cleared. */
  filters: TransactionFilters | null;
  applyFilters: (filters: TransactionFilters) => void;
  clearFilters: () => void;
}

/** The applied filters, shared by the filter form and its results. */
export const useTransactionFilterStore = create<TransactionFilterState>((set) => ({
  filters: null,
  applyFilters: (filters) => set({ filters }),
  clearFilters: () => set({ filters: null }),
}));
