import React, { ReactNode } from 'react';
import { TouchableOpacity, View, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Text from '@/components/atoms/Text';

export type QuickActionVariant = 'primary' | 'default';

export interface QuickActionButtonProps {
  icon: ReactNode;
  label: string;
  onPress?: () => void;
  variant?: QuickActionVariant;
}

const QuickActionButton: React.FC<QuickActionButtonProps> = ({
  icon,
  label,
  onPress,
  variant = 'default',
}) => {
  const content = (
    <>
      <View style={styles.iconWrapper}>{icon}</View>
      <Text variant="body12" color="#242D35" align="center" style={styles.label}>
        {label}
      </Text>
    </>
  );

  if (variant === 'primary') {
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.7} style={styles.touchable}>
        <LinearGradient
          colors={['#2FDAFF', '#0E33F3']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={[styles.card, styles.brandShadow]}
        >
          {content}
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      style={[styles.touchable, styles.card, styles.defaultCard, styles.cardShadow]}
    >
      {content}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  touchable: {
    width: 160,
  },
  card: {
    borderRadius: 16,
    padding: 16,
    alignItems: 'center',
    width: 160,
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
    marginBottom: 8,
    alignItems: 'center',
  },
  label: {
    textAlign: 'center',
  },
});

export default QuickActionButton;
