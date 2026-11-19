/**
 * ProgressBar atom — Masroofy design system
 * value: 0–100, rounded corners, configurable colors.
 */
import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

export interface ProgressBarProps {
  value: number;
  height?: number;
  color?: string;
  trackColor?: string;
  style?: StyleProp<ViewStyle>;
}

const ProgressBar: React.FC<ProgressBarProps> = ({
  value,
  height = 8,
  color = '#0E33F3',
  trackColor = '#EBEEF0',
  style,
}) => {
  const clamped = Math.min(100, Math.max(0, value));
  const radius = height / 2;

  return (
    <View
      style={[
        styles.track,
        {
          height,
          backgroundColor: trackColor,
          borderRadius: radius,
        },
        style,
      ]}
    >
      <View
        style={[
          styles.fill,
          {
            width: `${clamped}%`,
            height,
            backgroundColor: color,
            borderRadius: radius,
          },
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  track: {
    width: '100%',
    overflow: 'hidden',
  } as ViewStyle,
  fill: {} as ViewStyle,
});

export default ProgressBar;
