import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';

export interface SectionHeaderProps {
  title: string;
  /** Trailing link label, e.g. "View All". Rendered only with `onAction`. */
  actionLabel?: string;
  onAction?: () => void;
  /** Passive count/summary on the right, e.g. "2 unread" or "6 budgets". */
  trailingText?: string;
}

const SectionHeader: React.FC<SectionHeaderProps> = ({ title, actionLabel, onAction, trailingText }) => (
  <View style={styles.container}>
    <AppText variant="subheading16" accessibilityRole="header">
      {title}
    </AppText>
    {actionLabel && onAction ? (
      <Pressable onPress={onAction} hitSlop={12} accessibilityRole="link">
        {({ pressed }) => (
          <AppText variant="body14" color={colors.primary} style={pressed && styles.pressed}>
            {actionLabel}
          </AppText>
        )}
      </Pressable>
    ) : trailingText ? (
      <AppText variant="subheading14" color={colors.text.secondary}>
        {trailingText}
      </AppText>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  container: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  pressed: { opacity: 0.6 },
});

export default SectionHeader;
