import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from './Text';
import Icon, { IconName } from './Icon';

export type ChipTone = 'info' | 'success' | 'error' | 'warning';

export interface ChipProps {
  label: string;
  tone?: ChipTone;
  /** Leading glyph, e.g. `trending-down` on a "11.1% less than September" trend chip. */
  icon?: IconName;
  style?: StyleProp<ViewStyle>;
}

const Chip: React.FC<ChipProps> = ({ label, tone = 'info', icon, style }) => {
  const { background, foreground } = colors.tone[tone];

  return (
    <View style={[styles.base, { backgroundColor: background }, style]}>
      {icon ? <Icon name={icon} size={14} color={foreground} /> : null}
      <AppText variant="subheading12" color={foreground}>
        {label}
      </AppText>
    </View>
  );
};

const styles = StyleSheet.create({
  base: {
    alignSelf: 'flex-start',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    borderRadius: radii.full,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
});

export default Chip;
