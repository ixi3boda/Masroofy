import React, { useRef } from 'react';
import { StyleProp, StyleSheet, TextInput, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import OtpDigitBox from '@components/atoms/OtpDigitBox';

export interface OtpCodeFieldProps {
  label?: string;
  length?: number;
  value: string[];
  onChange: (digits: string[]) => void;
  filled?: boolean;
  style?: StyleProp<ViewStyle>;
}

const OtpCodeField: React.FC<OtpCodeFieldProps> = ({
  label,
  length = 6,
  value,
  onChange,
  filled = false,
  style,
}) => {
  const inputs = useRef<(TextInput | null)[]>([]);

  const setDigit = (index: number, digit: string) => {
    const next = [...value];
    next[index] = digit;
    onChange(next);
    if (digit && index < length - 1) {
      inputs.current[index + 1]?.focus();
    }
  };

  const handleKeyPress = (index: number, key: string) => {
    if (key === 'Backspace' && !value[index] && index > 0) {
      inputs.current[index - 1]?.focus();
    }
  };

  return (
    <View style={[styles.container, style]}>
      {label ? <AppText variant="body14" color={colors.text.primary}>{label}</AppText> : null}
      <View style={styles.row}>
        {Array.from({ length }).map((_, index) => (
          <OtpDigitBox
            key={index}
            ref={(ref) => {
              inputs.current[index] = ref;
            }}
            value={value[index] ?? ''}
            onChangeText={(digit) => setDigit(index, digit)}
            onKeyPress={({ nativeEvent }) => handleKeyPress(index, nativeEvent.key)}
            filled={filled}
          />
        ))}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { width: '100%', gap: 12 },
  row: { flexDirection: 'row', gap: 8, width: '100%' },
});

export default OtpCodeField;
