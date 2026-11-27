import { create } from 'zustand';

interface PasswordResetState {
  /** Single-use token from the reset-code screen. Memory only: never in route params (they land in the URL on web) or on disk. */
  resetToken: string | null;
  setResetToken: (resetToken: string) => void;
  clear: () => void;
}

/** The in-progress "forgot password" flow, between the code screen and the new-password screen. */
export const usePasswordResetStore = create<PasswordResetState>((set) => ({
  resetToken: null,
  setResetToken: (resetToken) => set({ resetToken }),
  clear: () => set({ resetToken: null }),
}));
