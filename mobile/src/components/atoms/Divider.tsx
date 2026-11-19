/**
 * Divider atom — Masroofy design system
 * Horizontal rule with configurable color and thickness.
 */
import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';

export interface DividerProps {
  color?: string;
  thickness?: number;
  style?: StyleProp<ViewStyle>;
}

const Divider: React.FC<DividerProps> = ({
  color = '#EBEEF0',
  thickness = 1,
  style,
}) => (
  <View
    style={[
      styles.base,
      { borderBottomColor: color, borderBottomWidth: thickness },
      style,
    ]}
  />
);

const styles = StyleSheet.create({
  base: {
    width: '100%',
  } as ViewStyle,
});

export default Divider;
