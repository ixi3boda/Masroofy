import React from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon, { IconName } from '@components/atoms/Icon';

export interface TabBarItemProps {
  label: string;
  icon: IconName;
  active?: boolean;
  onPress?: () => void;
}

const TabBarItem: React.FC<TabBarItemProps> = ({ label, icon, active = false, onPress }) => (
  <Pressable
    onPress={onPress}
    accessibilityRole="tab"
    accessibilityLabel={label}
    accessibilityState={{ selected: active }}
    style={({ pressed }) => [styles.container, pressed && styles.pressed]}
  >
    <Icon name={icon} color={active ? colors.primary : colors.text.muted} />
    <AppText variant="caption10" color={active ? colors.primary : colors.text.tab} numberOfLines={1}>
      {label}
    </AppText>
  </Pressable>
);

const styles = StyleSheet.create({
  container: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: 4,
    paddingVertical: 6,
    minHeight: 52,
  },
  pressed: { opacity: 0.6 },
});

export default TabBarItem;
