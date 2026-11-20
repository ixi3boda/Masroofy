import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import IconButton from '@components/atoms/IconButton';

export interface ScreenHeaderProps {
  title: string;
  onBack?: () => void;
  /** Replaces the back arrow, e.g. a "Cancel" link on edit screens. */
  left?: ReactNode;
  /** Trailing action, e.g. a profile button or a compact "Save Changes" button. */
  right?: ReactNode;
  /** center = stack screens (default) · start = top-level tab screens like Home. */
  titleAlign?: 'center' | 'start';
  style?: StyleProp<ViewStyle>;
}

const SIDE_MIN_WIDTH = 40;

/**
 * App-wide screen header. Centered titles keep equal-width side slots so the
 * title stays centered whether or not a back button or action is present.
 */
const ScreenHeader: React.FC<ScreenHeaderProps> = ({ title, onBack, left, right, titleAlign = 'center', style }) => {
  const centered = titleAlign === 'center';
  const leading =
    left ?? (onBack ? <IconButton name="chevron-left" accessibilityLabel="Go back" onPress={onBack} size={32} /> : null);

  return (
    <View style={[styles.container, style]}>
      {centered || leading ? <View style={centered && styles.side}>{leading}</View> : null}
      <AppText
        variant="subheading18"
        align={centered ? 'center' : 'left'}
        numberOfLines={1}
        accessibilityRole="header"
        style={styles.title}
      >
        {title}
      </AppText>
      {centered || right ? <View style={[centered && styles.side, styles.trailing]}>{right}</View> : null}
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

export default ScreenHeader;
