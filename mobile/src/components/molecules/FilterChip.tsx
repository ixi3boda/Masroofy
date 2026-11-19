import React from 'react';
import { ScrollView, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import Chip from '@/components/atoms/Chip';

export interface FilterChipProps {
  options: string[];
  selected: string;
  onSelect: (option: string) => void;
  style?: StyleProp<ViewStyle>;
}

const FilterChip: React.FC<FilterChipProps> = ({ options, selected, onSelect, style }) => {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.contentContainer}
      style={style}
    >
      {options.map((option) => (
        <Chip
          key={option}
          label={option}
          selected={selected === option}
          onPress={() => onSelect(option)}
          style={styles.chip}
        />
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  contentContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 2,
  },
  chip: {},
});

export default FilterChip;
