import React from 'react';
import { Pressable, StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients } from '@theme/index';
import AppText from './Text';

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  style?: StyleProp<ViewStyle>;
}

/** Equal-width single-choice switch, e.g. All / Expenses / Income. */
const SegmentedControl = <T extends string>({ options, value, onChange, style }: SegmentedControlProps<T>) => (
  <View style={[styles.track, style]} accessibilityRole="tablist">
    {options.map((option) => {
      const selected = option.value === value;
      const label = (
        <AppText variant="subheading13" align="center" color={selected ? colors.text.inverse : colors.text.secondary}>
          {option.label}
        </AppText>
      );

      return (
        <Pressable
          key={option.value}
          onPress={() => onChange(option.value)}
          accessibilityRole="tab"
          accessibilityState={{ selected }}
          style={styles.segment}
        >
          {selected ? (
            <LinearGradient
              colors={gradients.icon.colors}
              start={gradients.icon.start}
              end={gradients.icon.end}
              style={styles.choice}
            >
              {label}
            </LinearGradient>
          ) : (
            <View style={styles.choice}>{label}</View>
          )}
        </Pressable>
      );
    })}
  </View>
);

const styles = StyleSheet.create({
  track: {
    width: '100%',
    flexDirection: 'row',
    gap: 4,
    padding: 4,
    borderRadius: 14,
    backgroundColor: colors.surfaceMuted,
  },
  segment: { flex: 1 },
  choice: {
    minHeight: 40,
    justifyContent: 'center',
    paddingHorizontal: 6,
    borderRadius: 10,
  },
});

export default SegmentedControl;
