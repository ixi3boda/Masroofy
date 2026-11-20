import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';

/** brand = on track · danger = limit reached or exceeded. */
export type ProgressBarTone = 'brand' | 'danger';

export interface ProgressBarProps {
  /** Fraction complete, 0–1. Values outside the range are clamped. */
  progress: number;
  tone?: ProgressBarTone;
  style?: StyleProp<ViewStyle>;
}

const FILL: Record<ProgressBarTone, string> = {
  brand: colors.primary,
  danger: colors.danger,
};

const ProgressBar: React.FC<ProgressBarProps> = ({ progress, tone = 'brand', style }) => {
  const clamped = Math.min(Math.max(progress, 0), 1);

  return (
    <View
      style={[styles.track, style]}
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: Math.round(clamped * 100) }}
    >
      <View style={[styles.fill, { width: `${clamped * 100}%`, backgroundColor: FILL[tone] }]} />
    </View>
  );
};

const styles = StyleSheet.create({
  track: {
    width: '100%',
    height: 8,
    borderRadius: 4,
    backgroundColor: colors.surfaceMuted,
    overflow: 'hidden',
  },
  fill: {
    height: '100%',
    borderRadius: 4,
  },
});

export default ProgressBar;
