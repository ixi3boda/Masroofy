import { create } from 'zustand';
import { AuthUser } from '@/types/auth';

interface SessionState {
  user: AuthUser | null;
  /** True once the app-start session check (stored refresh token) has finished. */
  sessionChecked: boolean;
  signIn: (user: AuthUser) => void;
  signOut: () => void;
  finishSessionCheck: () => void;
}

/**
 * Who is signed in. The root navigator guards the (auth) and (app) groups on
 * this, so once a user signs in the auth screens leave the history and the
 * back button can never return to them. Tokens never live here: the API layer
 * keeps them (memory + secure storage).
 */
export const useSessionStore = create<SessionState>((set) => ({
  user: null,
  sessionChecked: false,
  signIn: (user) => set({ user }),
  signOut: () => set({ user: null }),
  finishSessionCheck: () => set({ sessionChecked: true }),
}));
