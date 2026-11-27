import { router as expoRouter } from 'expo-router';

/**
 * A navigation started less than this long after the previous one is dropped, so a
 * double-tap opens (or closes) one screen, not two. Shorter than any real
 * tap → read → tap sequence, longer than a stack transition.
 */
const NAVIGATION_COOLDOWN_MS = 400;

let lastNavigationAt = 0;

const guarded =
  <A extends unknown[]>(navigate: (...args: A) => void) =>
  (...args: A) => {
    const now = Date.now();
    if (now - lastNavigationAt < NAVIGATION_COOLDOWN_MS) return;
    lastNavigationAt = now;
    navigate(...args);
  };

/** Expo Router's `router`, with repeated taps ignored. Screens and hooks navigate through this, never `expo-router` directly. */
export const router = {
  push: guarded((...args: Parameters<typeof expoRouter.push>) => expoRouter.push(...args)),
  replace: guarded((...args: Parameters<typeof expoRouter.replace>) => expoRouter.replace(...args)),
  dismissTo: guarded((...args: Parameters<typeof expoRouter.dismissTo>) => expoRouter.dismissTo(...args)),
  back: guarded(() => expoRouter.back()),
  canGoBack: () => expoRouter.canGoBack(),
};
