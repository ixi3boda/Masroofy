import React, { Children, ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';

export interface FieldRowProps {
  /** Two (or more) short fields shown side by side with equal widths, e.g. Time + Repeat. */
  children: ReactNode;
}

const FieldRow: React.FC<FieldRowProps> = ({ children }) => (
  <View style={styles.row}>
    {Children.toArray(children).map((child, index) => (
      <View key={index} style={styles.cell}>
        {child}
      </View>
    ))}
  </View>
);

const styles = StyleSheet.create({
  row: { width: '100%', flexDirection: 'row', gap: 12 },
  cell: { flex: 1 },
});

export default FieldRow;
