import React from 'react';
import {
  ActivityIndicator,
  StyleProp,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients, radii } from '@theme/index';
import AppText from './Text';

export type ButtonVariant = 'primary' | 'outline';

export interface ButtonProps {
  title: string;
  variant?: ButtonVariant;
  loading?: boolean;
  disabled?: boolean;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

const Button: React.FC<ButtonProps> = ({
  title,
  variant = 'primary',
  loading = false,
  disabled = false,
  onPress,
  style,
}) => {
  const isDisabled = disabled || loading;

  const label = loading ? (
    <ActivityIndicator color={variant === 'primary' ? colors.text.inverse : colors.primary} />
  ) : (
    <AppText variant="subheading16" color={variant === 'primary' ? colors.text.inverse : colors.primary}>
      {title}
    </AppText>
  );

  if (variant === 'primary') {
    return (
      <TouchableOpacity
        onPress={onPress}
        disabled={isDisabled}
        activeOpacity={0.85}
        style={[isDisabled && styles.disabled, style]}
      >
        <LinearGradient
          colors={gradients.button.colors}
          start={gradients.button.start}
          end={gradients.button.end}
          style={styles.base}
        >
          {label}
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.75}
      style={[styles.base, styles.outline, isDisabled && styles.disabled, style]}
    >
      {label}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  base: {
    height: 48,
    borderRadius: radii.md,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: 20,
    width: '100%',
  },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 0.5,
    borderColor: colors.primary,
  },
  disabled: {
    opacity: 0.5,
  },
});

export default Button;
