import React from 'react';
import { StyleSheet, View } from 'react-native';
import { IconName } from '@components/atoms/Icon';
import OptionCard from '@components/molecules/OptionCard';
import { strings } from '@/strings';

export interface OptionListItem<T extends string> {
  value: T;
  title: string;
  /** Always-visible helper line, e.g. "Money moved between your own funds". */
  description?: string;
  icon?: IconName;
}

export interface OptionListProps<T extends string> {
  options: OptionListItem<T>[];
  /** `null` when nothing is chosen yet (e.g. an unclassified withdrawal). */
  value: T | null;
  onChange: (value: T) => void;
}

/** Single-select list of option cards (category picker, filters, classification, schedule). */
const OptionList = <T extends string>({ options, value, onChange }: OptionListProps<T>) => (
  <View style={styles.list} accessibilityRole="radiogroup">
    {options.map((option) => {
      const selected = option.value === value;
      return (
        <OptionCard
          key={option.value}
          title={option.title}
          icon={option.icon}
          description={option.description ?? (selected ? strings.common.selected : undefined)}
          selected={selected}
          onPress={() => onChange(option.value)}
        />
      );
    })}
  </View>
);

const styles = StyleSheet.create({
  list: { width: '100%', gap: 12 },
});

export default OptionList;
