import { create } from 'zustand';
import { AuthUser } from '@/types/auth';

interface SessionState {
  user: AuthUser | null;
  signIn: (user: AuthUser) => void;
}

/**
 * Who is signed in. The root navigator guards the (auth) and (app) groups on
 * this, so once a user signs in the auth screens leave the history and the
 * back button can never return to them.
 */
export const useSessionStore = create<SessionState>((set) => ({
  user: null,
  signIn: (user) => set({ user }),
}));
