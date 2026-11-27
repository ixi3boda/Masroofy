import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { colors } from '@theme/index';
import AppText from './Text';

export interface ProgressRingProps {
  /** Fraction complete, 0–1. Values outside the range are clamped. */
  progress: number;
  size?: number;
  strokeWidth?: number;
}

/** Circular progress with the percentage centred (savings goal detail). */
const ProgressRing: React.FC<ProgressRingProps> = ({ progress, size = 140, strokeWidth = 12 }) => {
  const clamped = Math.min(Math.max(progress, 0), 1);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const percent = Math.round(clamped * 100);

  return (
    <View
      style={{ width: size, height: size }}
      accessibilityRole="progressbar"
      accessibilityValue={{ min: 0, max: 100, now: percent }}
    >
      <Svg width={size} height={size}>
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.surfaceMuted}
          strokeWidth={strokeWidth}
          fill="none"
        />
        <Circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          stroke={colors.primary}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={`${circumference} ${circumference}`}
          strokeDashoffset={circumference * (1 - clamped)}
          fill="none"
          // Start the arc at 12 o'clock instead of 3 o'clock.
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
        />
      </Svg>
      <View style={StyleSheet.absoluteFill}>
        <View style={styles.center}>
          <AppText variant="h1" color={colors.primary}>
            {percent}%
          </AppText>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  center: { flex: 1, alignItems: 'center', justifyContent: 'center' },
});

export default ProgressRing;
