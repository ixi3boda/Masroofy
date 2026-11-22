import React from 'react';
import { StyleSheet, View } from 'react-native';
import ListRow from '@components/molecules/ListRow';

export interface DetailListProps {
  /** Labels must be unique. */
  details: { label: string; value: string }[];
}

/** Key–value lines that read as one block, with no dividers between them (Account, Category, Status…). */
const DetailList: React.FC<DetailListProps> = ({ details }) => (
  <View style={styles.list}>
    {details.map(({ label, value }) => (
      <ListRow key={label} title={label} trailing={value} />
    ))}
  </View>
);

const styles = StyleSheet.create({
  list: { width: '100%', gap: 14 },
});

export default DetailList;
