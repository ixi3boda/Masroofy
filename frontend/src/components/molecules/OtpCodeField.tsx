import React, { useLayoutEffect, useRef } from 'react';
import { StyleProp, StyleSheet, TextInputInstance, View, ViewStyle } from 'react-native';
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

/** What a box's text means: the box's old digit plus what was typed or pasted next to it. */
const incomingDigits = (text: string, current: string): string => {
  if (!current || text.length < 2) return text;
  if (text.startsWith(current)) return text.slice(current.length);
  if (text.endsWith(current)) return text.slice(0, -current.length);
  return text;
};

const OtpCodeField: React.FC<OtpCodeFieldProps> = ({
  label,
  length = 6,
  value,
  onChange,
  filled = false,
  style,
}) => {
  const inputs = useRef<(TextInputInstance | null)[]>([]);
  // Newest digits, also between renders, so fast typing never writes over a digit just entered.
  const latest = useRef(value);
  useLayoutEffect(() => {
    latest.current = value;
  }, [value]);

  const handleChange = (index: number, text: string) => {
    const next = [...latest.current];
    const incoming = incomingDigits(text, next[index] ?? '');

    if (!incoming) {
      next[index] = '';
    } else {
      // One digit typed, or a whole code pasted / autofilled: fill this box and the ones after it.
      incoming
        .slice(0, length - index)
        .split('')
        .forEach((digit, offset) => {
          next[index + offset] = digit;
        });
    }

    latest.current = next;
    onChange(next);
    if (incoming) inputs.current[Math.min(index + incoming.length, length - 1)]?.focus();
  };

  const handleKeyPress = (index: number, key: string) => {
    if (key === 'Backspace' && !latest.current[index] && index > 0) {
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
            onChangeText={(text) => handleChange(index, text)}
            onKeyPress={({ nativeEvent }) => handleKeyPress(index, nativeEvent.key)}
            autoFillCode={index === 0}
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
