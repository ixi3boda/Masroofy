import React from 'react';
import { StyleSheet, View } from 'react-native';
import ActionChip, { ActionChipProps } from '@components/molecules/ActionChip';
import SectionHeader from '@components/molecules/SectionHeader';

export interface ActionChipGroupProps {
  title: string;
  /** Wrapped into as many rows as the screen width needs; labels must be unique. */
  actions: ActionChipProps[];
}

const ActionChipGroup: React.FC<ActionChipGroupProps> = ({ title, actions }) => (
  <View style={styles.container}>
    <SectionHeader title={title} />
    <View style={styles.wrap}>
      {actions.map((action) => (
        <ActionChip key={action.label} {...action} />
      ))}
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: { width: '100%', gap: 16 },
  wrap: { flexDirection: 'row', flexWrap: 'wrap', gap: 12 },
});

export default ActionChipGroup;
