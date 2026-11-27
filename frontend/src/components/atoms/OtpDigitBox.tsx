import React, { forwardRef } from 'react';
import { StyleSheet, TextInput, TextInputInstance, TextInputProps } from 'react-native';
import { colors, radii } from '@theme/index';

export interface OtpDigitBoxProps extends Pick<TextInputProps, 'onKeyPress'> {
  value: string;
  /** Every digit the box received: one when typed, several when a code is pasted or autofilled. */
  onChangeText: (digits: string) => void;
  /** Offer the OS one-time-code autofill on this box (the first one). */
  autoFillCode?: boolean;
  /** Muted background used on the "verify email" code entry; white on the rest. */
  filled?: boolean;
}

const OtpDigitBox = forwardRef<TextInputInstance, OtpDigitBoxProps>(
  ({ value, onChangeText, onKeyPress, autoFillCode = false, filled = false }, ref) => {
    return (
      <TextInput
        ref={ref}
        value={value}
        onChangeText={(text) => onChangeText(text.replace(/[^0-9]/g, ''))}
        onKeyPress={onKeyPress}
        keyboardType="number-pad"
        autoComplete={autoFillCode ? 'one-time-code' : 'off'}
        textContentType={autoFillCode ? 'oneTimeCode' : 'none'}
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
