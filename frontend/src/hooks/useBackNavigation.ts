import { useCallback } from 'react';
import { BackHandler } from 'react-native';
import { Href, useFocusEffect } from 'expo-router';
import { router } from '@/navigation/router';

/**
 * Back action that never dead-ends: pops the stack when there is history,
 * otherwise (deep link, web refresh, cold start) replaces with `fallback`.
 */
export const useGoBack = (fallback: Href) =>
  useCallback(() => {
    if (router.canGoBack()) {
      router.back();
    } else {
      router.replace(fallback);
    }
  }, [fallback]);

/**
 * Routes the Android hardware back button to `onBack` so it matches the
 * on-screen back arrow. Active only while the screen is focused, so a screen
 * pushed on top keeps the normal back behaviour. No-op on iOS and web.
 */
export const useHardwareBack = (onBack: () => void) => {
  useFocusEffect(
    useCallback(() => {
      const subscription = BackHandler.addEventListener('hardwareBackPress', () => {
        onBack();
        return true;
      });
      return () => subscription.remove();
    }, [onBack]),
  );
};
