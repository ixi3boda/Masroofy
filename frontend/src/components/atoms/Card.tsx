import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients, radii, shadows } from '@theme/index';

/** default = white elevated surface; brand = gradient highlight surface. */
export type CardVariant = 'default' | 'brand';

export interface CardProps {
  children: ReactNode;
  variant?: CardVariant;
  style?: StyleProp<ViewStyle>;
}

const Card: React.FC<CardProps> = ({ children, variant = 'default', style }) => {
  if (variant === 'brand') {
    return (
      <LinearGradient
        colors={gradients.icon.colors}
        start={gradients.icon.start}
        end={gradients.icon.end}
        style={[styles.card, styles.brand, style]}
      >
        {children}
      </LinearGradient>
    );
  }

  return <View style={[styles.card, style]}>{children}</View>;
};

const styles = StyleSheet.create({
  card: {
    width: '100%',
    gap: 14,
    padding: 20,
    borderRadius: radii.xxl,
    backgroundColor: colors.surface,
    ...shadows.card,
  },
  brand: {
    backgroundColor: 'transparent',
    ...shadows.brand,
  },
});

export default Card;
