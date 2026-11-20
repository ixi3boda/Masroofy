import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';

export interface MonthTimelineProps {
  /** Short month labels in order, e.g. ["Nov", "Dec", "Jan"]. */
  months: string[];
}

/** Evenly spaced dots marking each planned month (savings planning guide). */
const MonthTimeline: React.FC<MonthTimelineProps> = ({ months }) => (
  <View style={styles.row} accessible accessibilityLabel={`Planned months: ${months.join(', ')}`}>
    {months.map((month) => (
      <View key={month} style={styles.item}>
        <View style={styles.dot} />
        <AppText variant="body12" color={colors.text.secondary}>
          {month}
        </AppText>
      </View>
    ))}
  </View>
);

const styles = StyleSheet.create({
  row: { width: '100%', flexDirection: 'row', justifyContent: 'space-between' },
  item: { alignItems: 'center', gap: 8 },
  dot: { width: 8, height: 8, borderRadius: 4, backgroundColor: colors.primary },
});

export default MonthTimeline;
