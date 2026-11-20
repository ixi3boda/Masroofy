import React from 'react';
import { StyleSheet, View } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients } from '@theme/index';

/**
 * brand = gradient (Home income bar) · muted = grey comparison bar
 * primary / accent = solid series colours for multi-series charts.
 */
export type ChartBarTone = 'brand' | 'muted' | 'primary' | 'accent';

export interface ChartBarProps {
  height: number;
  tone?: ChartBarTone;
  width?: number;
}

const SOLID: Record<Exclude<ChartBarTone, 'brand'>, string> = {
  muted: colors.text.disabled,
  primary: colors.primary,
  accent: colors.chart.accent,
};

const ChartBar: React.FC<ChartBarProps> = ({ height, tone = 'brand', width = 40 }) =>
  tone === 'brand' ? (
    <LinearGradient
      colors={gradients.icon.colors}
      start={gradients.icon.start}
      end={gradients.icon.end}
      style={[styles.bar, { height, width }]}
    />
  ) : (
    <View style={[styles.bar, { height, width, backgroundColor: SOLID[tone] }]} />
  );

const styles = StyleSheet.create({
  bar: {
    borderTopLeftRadius: 4,
    borderTopRightRadius: 4,
  },
});

export default ChartBar;
