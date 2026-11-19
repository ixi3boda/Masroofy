import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radii, shadows } from '@theme/index';

export interface CardProps {
  children: ReactNode;
  style?: StyleProp<ViewStyle>;
}

const Card: React.FC<CardProps> = ({ children, style }) => (
  <View style={[styles.card, style]}>{children}</View>
);

const styles = StyleSheet.create({
  card: {
    width: '100%',
    gap: 14,
    padding: 20,
    borderRadius: radii.xxl,
    backgroundColor: colors.surface,
    ...shadows.card,
  },
});

export default Card;
