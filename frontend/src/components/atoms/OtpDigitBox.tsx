import React, { forwardRef } from 'react';
import { StyleSheet, TextInput, TextInputProps } from 'react-native';
import { colors, radii } from '@theme/index';

export interface OtpDigitBoxProps extends Pick<TextInputProps, 'onKeyPress'> {
  value: string;
  onChangeText: (text: string) => void;
  /** Muted background used on the "verify email" code entry; white on the rest. */
  filled?: boolean;
}

const OtpDigitBox = forwardRef<TextInput, OtpDigitBoxProps>(
  ({ value, onChangeText, onKeyPress, filled = false }, ref) => {
    return (
      <TextInput
        ref={ref}
        value={value}
        onChangeText={(text) => onChangeText(text.replace(/[^0-9]/g, '').slice(-1))}
        onKeyPress={onKeyPress}
        maxLength={1}
        keyboardType="number-pad"
        textAlign="center"
        style={[styles.box, filled && styles.filled]}
      />
    );
  }
);
OtpDigitBox.displayName = 'OtpDigitBox';

const styles = StyleSheet.create({
  box: {
    flex: 1,
    minWidth: 0,
    height: 48,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border.otp,
    backgroundColor: colors.surface,
    fontFamily: 'Inter_400Regular',
    fontSize: 20,
    letterSpacing: 0.4,
    color: colors.text.primary,
  },
  filled: {
    height: 52,
    backgroundColor: colors.background,
  },
});

export default OtpDigitBox;
