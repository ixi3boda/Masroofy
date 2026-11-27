import { useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';

/**
 * The selected tab of a tabbed screen, first of `tabs` by default. It is local
 * state so a tap switches in the same frame; `?tab=` only mirrors it, and is
 * followed when another screen opens this one on a given tab.
 */
export const useTabParam = <T extends string>(tabs: readonly T[]) => {
  const params = useLocalSearchParams<{ tab?: string }>();
  const requested = tabs.find((value) => value === params.tab) ?? tabs[0];

  const [tab, setTab] = useState<T>(requested);
  const [followed, setFollowed] = useState<T>(requested);
  if (requested !== followed) {
    setFollowed(requested);
    setTab(requested);
  }

  const changeTab = (value: T) => {
    setTab(value);
    router.setParams({ tab: value as string });
  };

  return [tab, changeTab] as const;
};
