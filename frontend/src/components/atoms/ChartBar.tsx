import React from 'react';
import { StyleSheet, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients } from '@theme/index';

export type ChartBarTone = 'brand' | 'muted';

export interface ChartBarProps {
  height: number;
  tone?: ChartBarTone;
}

const ChartBar: React.FC<ChartBarProps> = ({ height, tone = 'brand' }) =>
  tone === 'brand' ? (
    <LinearGradient
      colors={gradients.icon.colors}
      start={gradients.icon.start}
      end={gradients.icon.end}
      style={[styles.bar, { height }]}
    />
  ) : (
    <View style={[styles.bar, styles.muted, { height }]} />
  );

const styles = StyleSheet.create({
  bar: {
    width: 40,
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
  muted: { backgroundColor: colors.text.disabled },
});

export default ChartBar;
