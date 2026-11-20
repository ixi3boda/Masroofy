import React from 'react';
import { StyleSheet, View } from 'react-native';
import StatCard, { StatCardProps } from '@components/molecules/StatCard';

export interface StatCardRowProps {
  /** Rendered side by side with equal widths; labels must be unique. */
  items: StatCardProps[];
}

const StatCardRow: React.FC<StatCardRowProps> = ({ items }) => (
  <View style={styles.row}>
    {items.map((item) => (
      <StatCard key={item.label} {...item} />
    ))}
  </View>
);

const styles = StyleSheet.create({
  row: { width: '100%', flexDirection: 'row', gap: 16 },
});

export default StatCardRow;
