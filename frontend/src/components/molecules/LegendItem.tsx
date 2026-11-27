import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';

export interface LegendItemProps {
  color: string;
  label: string;
  /** Right-aligned figure, e.g. "EGP 5,000". */
  value?: string;
  /** Under the value, e.g. "40.2% of spending". */
  caption?: string;
}

/** Colour key for a chart series; compact when only `label` is given. */
const LegendItem: React.FC<LegendItemProps> = ({ color, label, value, caption }) => (
  <View style={[styles.row, value ? styles.full : null]} accessible accessibilityLabel={[label, value, caption].filter(Boolean).join(', ')}>
    <View style={[styles.dot, { backgroundColor: color }]} />
    <AppText variant="body14" style={value ? styles.label : undefined}>
      {label}
    </AppText>
    {value ? (
      <View style={styles.figures}>
        <AppText variant="subheading14">{value}</AppText>
        {caption ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {caption}
          </AppText>
        ) : null}
      </View>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  full: { width: '100%', gap: 12 },
  dot: { width: 8, height: 8, borderRadius: 4 },
  label: { flex: 1 },
  figures: { alignItems: 'flex-start', minWidth: 110 },
});

export default LegendItem;
