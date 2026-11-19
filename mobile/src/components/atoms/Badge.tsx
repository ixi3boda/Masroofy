/**
 * Badge atom — Masroofy design system
 * Variants: default | success | warning | error | brand (gradient)
 * Sizes:    sm | md
 */
import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import AppText from './Text';

// ─── Types ────────────────────────────────────────────────────────────────────
export type BadgeVariant = 'default' | 'success' | 'warning' | 'error' | 'brand';
export type BadgeSize = 'sm' | 'md';

export interface BadgeProps {
  label: string;
  variant?: BadgeVariant;
  size?: BadgeSize;
}

// ─── Token maps ───────────────────────────────────────────────────────────────
const BG_COLORS: Record<Exclude<BadgeVariant, 'brand'>, string> = {
  default: '#EBEEF0',
  success: '#E8F9F0',
  warning: '#FEF3C7',
  error: '#FEE2E2',
};

const TEXT_COLORS: Record<Exclude<BadgeVariant, 'brand'>, string> = {
  default: '#6B7580',
  success: '#10B981',
  warning: '#F59E0B',
  error: '#EF4E4E',
};

const SIZE_PADDING: Record<BadgeSize, { paddingVertical: number; paddingHorizontal: number }> = {
  sm: { paddingVertical: 6, paddingHorizontal: 10 },
  md: { paddingVertical: 8, paddingHorizontal: 14 },
};

// ─── Component ────────────────────────────────────────────────────────────────
const Badge: React.FC<BadgeProps> = ({ label, variant = 'default', size = 'md' }) => {
  const padding = SIZE_PADDING[size];
  const textColor = variant === 'brand' ? '#FFFFFF' : TEXT_COLORS[variant];

  const textNode = (
    <AppText variant="subheading12" color={textColor}>
      {label}
    </AppText>
  );

  if (variant === 'brand') {
    return (
      <LinearGradient
        colors={['#2FDAFF', '#0E33F3']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.base, padding]}
      >
        {textNode}
      </LinearGradient>
    );
  }

  return (
    <View style={[styles.base, padding, { backgroundColor: BG_COLORS[variant] }]}>
      {textNode}
    </View>
  );
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  base: {
    borderRadius: 100,
    alignSelf: 'flex-start',
    alignItems: 'center',
    justifyContent: 'center',
  } as ViewStyle,
});

export default Badge;
