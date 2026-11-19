import React from 'react';
import { StyleProp, StyleSheet, TouchableOpacity, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from './Text';

export interface CheckboxProps {
  checked: boolean;
  onToggle: (next: boolean) => void;
  size?: number;
  style?: StyleProp<ViewStyle>;
}

const Checkbox: React.FC<CheckboxProps> = ({ checked, onToggle, size = 20, style }) => {
  return (
    <TouchableOpacity
      accessibilityRole="checkbox"
      accessibilityState={{ checked }}
      activeOpacity={0.7}
      onPress={() => onToggle(!checked)}
      style={[
        styles.base,
        {
          width: size,
          height: size,
          borderRadius: size / 2,
          backgroundColor: checked ? colors.primary : 'transparent',
          borderColor: checked ? colors.primary : colors.border.otp,
        },
        style,
      ]}
    >
      {checked ? (
        <AppText variant="subheading12" color={colors.text.inverse} style={{ fontSize: size * 0.6, lineHeight: size * 0.7 }}>
          ✓
        </AppText>
      ) : null}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  base: {
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default Checkbox;
