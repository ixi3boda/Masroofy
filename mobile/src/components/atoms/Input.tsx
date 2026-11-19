/**
 * Input atom — Masroofy design system
 * White bg, 1px border (default #EBEEF0 / focus #0E33F3 / error #EF4E4E)
 * h48, r12, optional label above, error/hint below.
 */
import React, { ReactNode, useState } from 'react';
import {
  KeyboardTypeOptions,
  StyleProp,
  StyleSheet,
  TextInput,
  View,
  ViewStyle,
  TextStyle,
} from 'react-native';
import AppText from './Text';

// ─── Types ────────────────────────────────────────────────────────────────────
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

// ─── Design tokens ────────────────────────────────────────────────────────────
const COLORS = {
  border: '#EBEEF0',
  borderFocus: '#0E33F3',
  borderError: '#EF4E4E',
  surface: '#FFFFFF',
  label: '#242D35',
  placeholder: '#B0B8BF',
  error: '#EF4E4E',
  hint: '#6B7580',
};

// ─── Component ────────────────────────────────────────────────────────────────
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
    ? COLORS.borderError
    : focused
    ? COLORS.borderFocus
    : COLORS.border;

  return (
    <View style={[styles.wrapper, style]}>
      {/* Label */}
      {label ? (
        <AppText variant="subheading12" color={COLORS.label} style={styles.label}>
          {label}
        </AppText>
      ) : null}

      {/* Input row */}
      <View style={[styles.inputContainer, { borderColor }]}>
        {leftIcon ? <View style={styles.leftIcon}>{leftIcon}</View> : null}
        <TextInput
          style={[
            styles.input,
            leftIcon ? styles.inputWithLeft : undefined,
            rightIcon ? styles.inputWithRight : undefined,
          ]}
          value={value}
          onChangeText={onChangeText}
          placeholder={placeholder}
          placeholderTextColor={COLORS.placeholder}
          secureTextEntry={secureTextEntry}
          editable={editable}
          keyboardType={keyboardType}
          autoCapitalize={autoCapitalize}
          onFocus={() => setFocused(true)}
          onBlur={() => setFocused(false)}
        />
        {rightIcon ? <View style={styles.rightIcon}>{rightIcon}</View> : null}
      </View>

      {/* Error / hint */}
      {hasError && errorMessage ? (
        <AppText variant="body12" color={COLORS.error} style={styles.helper}>
          {errorMessage}
        </AppText>
      ) : hint ? (
        <AppText variant="body12" color={COLORS.hint} style={styles.helper}>
          {hint}
        </AppText>
      ) : null}
    </View>
  );
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  wrapper: {
    width: '100%',
  } as ViewStyle,
  label: {
    marginBottom: 6,
  } as TextStyle,
  inputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderWidth: 1,
    borderRadius: 12,
    height: 48,
    paddingHorizontal: 14,
  } as ViewStyle,
  input: {
    flex: 1,
    height: '100%',
    fontSize: 14,
    fontFamily: 'Inter-Regular',
    color: '#242D35',
    paddingVertical: 0, // Android fix
  } as TextStyle,
  inputWithLeft: {
    marginLeft: 8,
  } as TextStyle,
  inputWithRight: {
    marginRight: 8,
  } as TextStyle,
  leftIcon: {
    justifyContent: 'center',
    alignItems: 'center',
  } as ViewStyle,
  rightIcon: {
    justifyContent: 'center',
    alignItems: 'center',
  } as ViewStyle,
  helper: {
    marginTop: 4,
  } as TextStyle,
});

export default Input;
