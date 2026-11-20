import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';

export interface WaveformProps {
  /** Bar heights as fractions of `height`, 0–1 — e.g. recent microphone levels. */
  levels: number[];
  height?: number;
}

/** Vertical-bar audio level visualisation for voice entry. Decorative for screen readers. */
const Waveform: React.FC<WaveformProps> = ({ levels, height = 64 }) => (
  <View
    style={[styles.row, { height }]}
    accessibilityElementsHidden
    importantForAccessibility="no-hide-descendants"
  >
    {levels.map((level, index) => (
      <View
        // Bars are positional; their order never changes.
        key={index}
        style={[styles.bar, { height: Math.max(6, Math.min(level, 1) * height) }]}
      />
    ))}
  </View>
);

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 6 },
  bar: { width: 4, borderRadius: 2, backgroundColor: colors.primary },
});

export default Waveform;
