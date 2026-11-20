import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import Icon from './Icon';

export interface CheckboxProps {
  checked: boolean;
  size?: number;
}

/**
 * Visual checkbox indicator only — the surrounding row (OptionCard) owns the
 * press target and the `checkbox` accessibility role.
 */
const Checkbox: React.FC<CheckboxProps> = ({ checked, size = 20 }) => (
  <View
    style={[
      styles.base,
      {
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: checked ? colors.primary : 'transparent',
        borderColor: checked ? colors.primary : colors.border.otp,
      },
    ]}
  >
    {checked ? <Icon name="check" size={size * 0.6} color={colors.text.inverse} strokeWidth={3} /> : null}
  </View>
);

const styles = StyleSheet.create({
  base: {
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default Checkbox;
