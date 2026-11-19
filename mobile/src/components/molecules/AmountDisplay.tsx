import React from 'react';
import { View, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Text from '@/components/atoms/Text';

export type AmountDisplayVariant = 'default' | 'gradient';

export interface AmountDisplayProps {
  label: string;
  amount: string;
  variant?: AmountDisplayVariant;
  style?: StyleProp<ViewStyle>;
}

const AmountDisplay: React.FC<AmountDisplayProps> = ({
  label,
  amount,
  variant = 'default',
  style,
}) => {
  if (variant === 'gradient') {
    return (
      <LinearGradient
        colors={['#2FDAFF', '#0E33F3']}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={[styles.card, styles.brandShadow, style]}
      >
        <Text variant="body12" color="rgba(255,255,255,0.8)">{label}</Text>
        <Text variant="subheading18" color="#FFFFFF" style={styles.amount}>
          {amount}
        </Text>
      </LinearGradient>
    );
  }

  return (
    <View style={[styles.card, styles.defaultCard, styles.cardShadow, style]}>
      <Text variant="body12" color="#6B7580">{label}</Text>
      <Text variant="subheading18" color="#242D35" style={styles.amount}>
        {amount}
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    borderRadius: 20,
    padding: 16,
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
  amount: {
    marginTop: 4,
  },
});

export default AmountDisplay;
