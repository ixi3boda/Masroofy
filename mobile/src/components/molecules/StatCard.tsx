import React, { ReactNode } from 'react';
import { View, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Text from '@/components/atoms/Text';

export type StatCardVariant = 'default' | 'gradient';

export interface StatCardProps {
  icon: ReactNode;
  label: string;
  amount: string;
  variant?: StatCardVariant;
  style?: StyleProp<ViewStyle>;
}

const StatCard: React.FC<StatCardProps> = ({
  icon,
  label,
  amount,
  variant = 'default',
  style,
}) => {
  const content = (
    <>
      <View style={styles.iconWrapper}>{icon}</View>
      <Text
        variant="body12"
        color={variant === 'gradient' ? 'rgba(255,255,255,0.8)' : '#6B7580'}
        style={styles.label}
      >
        {label}
      </Text>
      <Text
        variant="subheading18"
        color={variant === 'gradient' ? '#FFFFFF' : '#242D35'}
        style={styles.amount}
      >
        {amount}
      </Text>
    </>
  );

  if (variant === 'gradient') {
    return (
      <LinearGradient
        colors={['#2FDAFF', '#0E33F3']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.card, styles.brandShadow, style]}
      >
        {content}
      </LinearGradient>
    );
  }

  return (
    <View style={[styles.card, styles.defaultCard, styles.cardShadow, style]}>
      {content}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    flex: 1,
    borderRadius: 20,
    padding: 20,
  },
  defaultCard: {
    backgroundColor: '#FFFFFF',
  },
  cardShadow: {
    shadowColor: '#1D3A58',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 32,
    elevation: 8,
  },
  brandShadow: {
    shadowColor: '#1D41F9',
    shadowOffset: { width: 0, height: 12 },
    shadowOpacity: 1,
    shadowRadius: 24,
    elevation: 12,
  },
  iconWrapper: {
    marginBottom: 12,
  },
  label: {
    marginBottom: 4,
  },
  amount: {},
});

export default StatCard;
