/**
 * Button atom — Masroofy design system
 * Variants: primary (gradient) | secondary (surface+shadow) | outline | ghost
 * Sizes:    sm | md (default) | lg
 */
import React, { ReactNode } from 'react';
import {
  ActivityIndicator,
  StyleSheet,
  TouchableOpacity,
  View,
  ViewStyle,
  TextStyle,
  StyleProp,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import AppText from './Text';

// ─── Design tokens ────────────────────────────────────────────────────────────
const COLORS = {
  primary: '#0E33F3',
  primaryLight: '#2FDAFF',
  surface: '#FFFFFF',
  text800: '#242D35',
  border: '#0E33F3',
};

const SHADOWS = {
  card: {
    shadowColor: '#1D3A58',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 32,
    elevation: 8,
  },
};

// ─── Types ────────────────────────────────────────────────────────────────────
export interface ButtonProps {
  title: string;
  variant?: 'primary' | 'secondary' | 'outline' | 'ghost';
  size?: 'sm' | 'md' | 'lg';
  loading?: boolean;
  disabled?: boolean;
  onPress?: () => void;
  leftIcon?: ReactNode;
  fullWidth?: boolean;
  style?: StyleProp<ViewStyle>;
}

// ─── Size maps ────────────────────────────────────────────────────────────────
const SIZE_STYLES: Record<
  'sm' | 'md' | 'lg',
  { paddingVertical: number; paddingHorizontal: number; fontSize: number }
> = {
  sm: { paddingVertical: 8, paddingHorizontal: 16, fontSize: 14 },
  md: { paddingVertical: 12, paddingHorizontal: 20, fontSize: 16 },
  lg: { paddingVertical: 16, paddingHorizontal: 24, fontSize: 18 },
};

// ─── Component ────────────────────────────────────────────────────────────────
const Button: React.FC<ButtonProps> = ({
  title,
  variant = 'primary',
  size = 'md',
  loading = false,
  disabled = false,
  onPress,
  leftIcon,
  fullWidth = false,
  style,
}) => {
  const sizeStyle = SIZE_STYLES[size];
  const isDisabled = disabled || loading;

  // Inner content (icon + label + spinner)
  const Content = () => (
    <View style={styles.row}>
      {leftIcon && !loading && <View style={styles.iconWrapper}>{leftIcon}</View>}
      {loading ? (
        <ActivityIndicator
          color={variant === 'primary' ? '#FFFFFF' : COLORS.primary}
          size="small"
        />
      ) : (
        <AppText
          variant={size === 'sm' ? 'subheading14' : size === 'lg' ? 'subheading18' : 'subheading16'}
          color={
            variant === 'primary'
              ? '#FFFFFF'
              : variant === 'outline' || variant === 'ghost'
              ? COLORS.primary
              : COLORS.text800
          }
          style={{ fontSize: sizeStyle.fontSize }}
        >
          {title}
        </AppText>
      )}
    </View>
  );

  // ── primary → LinearGradient wrapper ──────────────────────────────────────
  if (variant === 'primary') {
    return (
      <TouchableOpacity
        onPress={onPress}
        disabled={isDisabled}
        activeOpacity={0.85}
        style={[fullWidth && styles.fullWidth, style]}
      >
        <LinearGradient
          colors={['#2FDAFF', '#0E33F3']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[
            styles.base,
            {
              paddingVertical: sizeStyle.paddingVertical,
              paddingHorizontal: sizeStyle.paddingHorizontal,
              borderRadius: 14,
              opacity: isDisabled ? 0.5 : 1,
            },
          ]}
        >
          <Content />
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  // ── secondary / outline / ghost ───────────────────────────────────────────
  const variantStyle: ViewStyle =
    variant === 'secondary'
      ? { backgroundColor: COLORS.surface, ...SHADOWS.card, borderRadius: 14 }
      : variant === 'outline'
      ? {
          backgroundColor: 'transparent',
          borderWidth: 0.5,
          borderColor: COLORS.border,
          borderRadius: 14,
        }
      : { backgroundColor: 'transparent' }; // ghost

  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={isDisabled}
      activeOpacity={0.75}
      style={[
        styles.base,
        variantStyle,
        {
          paddingVertical: sizeStyle.paddingVertical,
          paddingHorizontal: sizeStyle.paddingHorizontal,
          opacity: isDisabled ? 0.5 : 1,
        },
        fullWidth && styles.fullWidth,
        style,
      ]}
    >
      <Content />
    </TouchableOpacity>
  );
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
    flexDirection: 'row',
  } as ViewStyle,
  fullWidth: {
    width: '100%',
  } as ViewStyle,
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  iconWrapper: {
    marginRight: 4,
  },
});

export default Button;
