import React, { ReactNode, useState } from 'react';
import {
  KeyboardTypeOptions,
  StyleProp,
  StyleSheet,
  TextInput,
  View,
  ViewStyle,
} from 'react-native';
import { colors } from '@theme/index';
import AppText from './Text';
import { fieldStyles } from './fieldStyles';

export interface InputProps {
  label?: string;
  placeholder?: string;
  value: string;
  onChangeText: (text: string) => void;
  hasError?: boolean;
  errorMessage?: string;
  hint?: string;
  secureTextEntry?: boolean;
  leftIcon?: ReactNode;
  rightIcon?: ReactNode;
  editable?: boolean;
  keyboardType?: KeyboardTypeOptions;
  autoCapitalize?: 'none' | 'sentences' | 'words' | 'characters';
  style?: StyleProp<ViewStyle>;
}

const Input: React.FC<InputProps> = ({
  label,
  placeholder,
  value,
  onChangeText,
  hasError = false,
  errorMessage,
  hint,
  secureTextEntry = false,
  leftIcon,
  rightIcon,
  editable = true,
  keyboardType,
  autoCapitalize,
  style,
}) => {
  const [focused, setFocused] = useState(false);

  const borderColor = hasError
    ? colors.tone.error.foreground
    : focused
    ? colors.primary
    : colors.border.default;

  return (
    <View style={[styles.wrapper, style]}>
      {label ? (
        <AppText variant="label12" color={colors.text.secondary} style={fieldStyles.label}>
          {label}
        </AppText>
      ) : null}

      <View style={[fieldStyles.box, { borderColor }]}>
        {leftIcon ? <View style={styles.sideIcon}>{leftIcon}</View> : null}
        <TextInput
          style={[fieldStyles.value, styles.input]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={colors.text.secondary}
          secureTextEntry={secureTextEntry}
          editable={editable}
          keyboardType={keyboardType}
          autoCapitalize={autoCapitalize}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />
        {rightIcon ? <View style={styles.sideIcon}>{rightIcon}</View> : null}
      </View>

      {hasError && errorMessage ? (
        <AppText variant="body12" color={colors.tone.error.foreground} style={fieldStyles.helper}>
          {errorMessage}
        </AppText>
      ) : hint ? (
        <AppText variant="body12" color={colors.text.secondary} style={fieldStyles.helper}>
          {hint}
        </AppText>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  wrapper: { width: '100%' },
  input: { height: '100%', paddingVertical: 0 },
  sideIcon: { alignItems: 'center', justifyContent: 'center' },
});

export default Input;
