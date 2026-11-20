import React from 'react';
import { StyleSheet, View } from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { colors, shadows } from '@theme/index';
import Fab from '@components/atoms/Fab';
import { IconName } from '@components/atoms/Icon';
import TabBarItem from '@components/molecules/TabBarItem';

export type TabKey = 'home' | 'savings' | 'reminders' | 'settings';

const TABS: { key: TabKey; label: string; icon: IconName }[] = [
  { key: 'home', label: 'Home', icon: 'home' },
  { key: 'savings', label: 'Savings', icon: 'piggy-bank' },
  { key: 'reminders', label: 'Reminders', icon: 'bell' },
  { key: 'settings', label: 'Settings', icon: 'settings' },
];

const MIDDLE = TABS.length / 2;

export interface BottomTabBarProps {
  activeTab: TabKey;
  onTabPress?: (tab: TabKey) => void;
  onAddPress?: () => void;
}

const BottomTabBar: React.FC<BottomTabBarProps> = ({ activeTab, onTabPress, onAddPress }) => {
  const { bottom } = useSafeAreaInsets();

  const renderTab = ({ key, label, icon }: (typeof TABS)[number]) => (
    <TabBarItem
      key={key}
      label={label}
      icon={icon}
      active={key === activeTab}
      onPress={onTabPress ? () => onTabPress(key) : undefined}
    />
  );

  return (
    <View style={[styles.container, { paddingBottom: Math.max(bottom, 8) }]} accessibilityRole="tablist">
      {TABS.slice(0, MIDDLE).map(renderTab)}
      <Fab accessibilityLabel="Add transaction" onPress={onAddPress} />
      {TABS.slice(MIDDLE).map(renderTab)}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    paddingTop: 4,
    backgroundColor: colors.surface,
    borderTopWidth: StyleSheet.hairlineWidth,
    borderTopColor: colors.border.default,
    ...shadows.card,
  },
});

export default BottomTabBar;
