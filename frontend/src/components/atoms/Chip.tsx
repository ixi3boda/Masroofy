import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from './Text';

export type ChipTone = 'info' | 'success' | 'error';

export interface ChipProps {
  label: string;
  tone?: ChipTone;
  style?: StyleProp<ViewStyle>;
}

const Chip: React.FC<ChipProps> = ({ label, tone = 'info', style }) => {
  const { background, foreground } = colors.tone[tone];

  return (
    <View style={[styles.base, { backgroundColor: background }, style]}>
      <AppText variant="subheading12" color={foreground}>
        {label}
      </AppText>
    </View>
  );
};

const styles = StyleSheet.create({
  base: {
    alignSelf: 'flex-start',
    borderRadius: radii.full,
    paddingHorizontal: 10,
    paddingVertical: 5,
  },
});

export default Chip;
