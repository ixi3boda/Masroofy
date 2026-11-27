import React from 'react';
import { StyleSheet, View } from 'react-native';
import QuickActionTile, { QuickActionTileProps } from '@components/molecules/QuickActionTile';
import SectionHeader from '@components/molecules/SectionHeader';

export interface QuickActionsGridProps {
  title: string;
  /** Laid out two per row; labels must be unique. */
  actions: Omit<QuickActionTileProps, 'style'>[];
}

const QuickActionsGrid: React.FC<QuickActionsGridProps> = ({ title, actions }) => (
  <View style={styles.container}>
    <SectionHeader title={title} />
    <View style={styles.grid}>
      {actions.map((action) => (
        <QuickActionTile key={action.label} {...action} style={styles.cell} />
      ))}
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: { width: '100%', gap: 16, paddingTop: 8 },
  grid: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
  // flexBasis < 50% + grow: exactly two columns that absorb the 12px gap.
  cell: { flexGrow: 1, flexBasis: '40%' },
});

export default QuickActionsGrid;
