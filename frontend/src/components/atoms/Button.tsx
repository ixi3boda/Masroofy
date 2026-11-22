import React from 'react';
import {
  ActivityIndicator,
  StyleProp,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients, radii, TypographyVariant } from '@theme/index';
import AppText from './Text';

/**
 * primary = gradient fill · outline = brand border · danger = red fill
 * link = brand text only · dangerLink = red text only (e.g. "Delete transaction")
 */
export type ButtonVariant = 'primary' | 'outline' | 'danger' | 'link' | 'dangerLink';

/** md = full-width footer action · sm = compact, content-width (e.g. header "Save Changes"). */
export type ButtonSize = 'md' | 'sm';

export interface ButtonProps {
  title: string;
  variant?: ButtonVariant;
  size?: ButtonSize;
  loading?: boolean;
  disabled?: boolean;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

const LABEL_COLOR: Record<ButtonVariant, string> = {
  primary: colors.text.inverse,
  danger: colors.text.inverse,
  outline: colors.primary,
  link: colors.primary,
  dangerLink: colors.danger,
};

const LABEL_VARIANT: Record<ButtonSize, TypographyVariant> = {
  md: 'subheading16',
  sm: 'subheading13',
};

const Button: React.FC<ButtonProps> = ({
  title,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  onPress,
  style,
}) => {
  const isDisabled = disabled || loading;
  const labelColor = LABEL_COLOR[variant];
  const sizeStyle = size === 'md' ? styles.md : styles.sm;

  const label = loading ? (
    <ActivityIndicator color={labelColor} />
  ) : (
    <AppText variant={LABEL_VARIANT[size]} color={labelColor}>
      {title}
    </AppText>
  );

  // Without a handler it keeps its look but can't be pressed; only `disabled` and `loading` dim it.
  const isInert = isDisabled || !onPress;
  const touchableProps = {
    onPress,
    disabled: isInert,
    accessibilityRole: 'button' as const,
    accessibilityState: { disabled: isInert, busy: loading },
  };

  if (variant === 'primary') {
    return (
      <TouchableOpacity {...touchableProps} activeOpacity={0.85} style={[isDisabled && styles.disabled, style]}>
        <LinearGradient
          colors={gradients.button.colors}
          start={gradients.button.start}
          end={gradients.button.end}
          style={[styles.base, sizeStyle]}
        >
          {label}
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      {...touchableProps}
      activeOpacity={0.75}
      style={[styles.base, sizeStyle, VARIANT_STYLE[variant], isDisabled && styles.disabled, style]}
    >
      {label}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  base: {
    borderRadius: radii.md,
    alignItems: 'center',
    justifyContent: 'center',
  },
  md: { height: 48, paddingHorizontal: 20, width: '100%' },
  sm: { height: 40, paddingHorizontal: 16, alignSelf: 'flex-start' },
  outline: {
    backgroundColor: 'transparent',
    borderWidth: 0.5,
    borderColor: colors.primary,
  },
  danger: { backgroundColor: colors.danger },
  disabled: { opacity: 0.5 },
});

const VARIANT_STYLE: Record<Exclude<ButtonVariant, 'primary'>, StyleProp<ViewStyle>> = {
  outline: styles.outline,
  danger: styles.danger,
  link: undefined,
  dangerLink: undefined,
};

export default Button;
