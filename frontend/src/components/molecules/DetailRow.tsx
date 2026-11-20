import React from 'react';
import { StyleSheet, View } from 'react-native';
import AppText from '@components/atoms/Text';

export interface DetailRowProps {
  label: string;
  value: string;
}

/** Label/value pair on one line, e.g. "Account — CIB debit •4821". */
const DetailRow: React.FC<DetailRowProps> = ({ label, value }) => (
  <View style={styles.row} accessible accessibilityLabel={`${label}: ${value}`}>
    <AppText variant="subheading14">{label}</AppText>
    <AppText variant="subheading14" align="right" numberOfLines={2} style={styles.value}>
      {value}
    </AppText>
  </View>
);

const styles = StyleSheet.create({
  row: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 12,
  },
  value: { flexShrink: 1 },
});

export default DetailRow;
