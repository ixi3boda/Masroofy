import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, TouchableOpacity, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon from '@components/atoms/Icon';

const SIDE_MIN_WIDTH = 32;

export interface AuthHeaderProps {
  title: string;
  onBack?: () => void;
  /** Replaces the back arrow, e.g. a "Cancel" link on edit screens. */
  left?: ReactNode;
  /** Trailing action, e.g. a compact "Save Changes" button. */
  right?: ReactNode;
  style?: StyleProp<ViewStyle>;
}

/**
 * Stack screen header: leading back/left slot, centered title, trailing slot.
 * Empty side slots keep a fixed width so the title stays centered.
 */
const AuthHeader: React.FC<AuthHeaderProps> = ({ title, onBack, left, right, style }) => {
  const leading =
    left ??
    (onBack ? (
      <TouchableOpacity onPress={onBack} hitSlop={8} accessibilityRole="button" accessibilityLabel="Go back">
        <Icon name="chevron-left" size={32} />
      </TouchableOpacity>
    ) : null);

  return (
    <View style={[styles.container, style]}>
      <View style={styles.side}>{leading}</View>
      <AppText variant="subheading18" align="center" numberOfLines={1} accessibilityRole="header" style={styles.title}>
        {title}
      </AppText>
      <View style={[styles.side, styles.trailing]}>{right}</View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    minHeight: 56,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingHorizontal: 16,
    backgroundColor: colors.surface,
  },
  side: { minWidth: SIDE_MIN_WIDTH },
  trailing: { alignItems: 'flex-end' },
  title: { flex: 1 },
});

export default AuthHeader;
