/**
 * Text atom — Masroofy design system
 * Covers all typography variants from the Figma token sheet.
 */
import React from 'react';
import {
  Text as RNText,
  TextProps as RNTextProps,
  TextStyle,
  StyleSheet,
} from 'react-native';

// ─── Types ────────────────────────────────────────────────────────────────────
export type TextVariant =
  | 'h1'
  | 'h2'
  | 'subheading18'
  | 'subheading16'
  | 'subheading14'
  | 'subheading12'
  | 'body14'
  | 'body12'
  | 'caption10';

export interface AppTextProps extends RNTextProps {
  variant?: TextVariant;
  color?: string;
  align?: TextStyle['textAlign'];
  children?: React.ReactNode;
  style?: TextStyle | TextStyle[];
}

// ─── Variant style map ────────────────────────────────────────────────────────
const VARIANT_STYLES: Record<TextVariant, TextStyle> = {
  h1: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 28,
    fontWeight: '600',
  },
  h2: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 22,
    fontWeight: '600',
  },
  subheading18: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 18,
    fontWeight: '600',
    lineHeight: 20,
    letterSpacing: 0.36,
  },
  subheading16: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 16,
    fontWeight: '600',
    lineHeight: 20,
  },
  subheading14: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 14,
    fontWeight: '600',
    lineHeight: 20,
  },
  subheading12: {
    fontFamily: 'Inter-SemiBold',
    fontSize: 12,
    fontWeight: '600',
    lineHeight: 16,
    letterSpacing: 0.24,
  },
  body14: {
    fontFamily: 'Inter-Regular',
    fontSize: 14,
    fontWeight: '400',
    lineHeight: 20,
    letterSpacing: 0.28,
  },
  body12: {
    fontFamily: 'Inter-Regular',
    fontSize: 12,
    fontWeight: '400',
    lineHeight: 16,
    letterSpacing: 0.24,
  },
  caption10: {
    fontFamily: 'Inter-Regular',
    fontSize: 10,
    fontWeight: '400',
    lineHeight: 12,
  },
};

// ─── Component ────────────────────────────────────────────────────────────────
const AppText: React.FC<AppTextProps> = ({
  variant = 'body14',
  color = '#242D35',
  align,
  children,
  style,
  ...rest
}) => {
  return (
    <RNText
      style={[
        styles.base,
        VARIANT_STYLES[variant],
        { color },
        align ? { textAlign: align } : undefined,
        style,
      ]}
      {...rest}
    >
      {children}
    </RNText>
  );
};

const styles = StyleSheet.create({
  base: {
    color: '#242D35',
  },
});

export default AppText;
