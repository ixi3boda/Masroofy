import React, { ReactNode } from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
import Text from '@/components/atoms/Text';

export interface TransactionItemProps {
  categoryIcon: ReactNode;
  title: string;
  metadata: string;
  amount: string;
  type?: 'expense' | 'income';
  onPress?: () => void;
}

const TransactionItem: React.FC<TransactionItemProps> = ({
  categoryIcon,
  title,
  metadata,
  amount,
  type = 'expense',
  onPress,
}) => {
  const amountColor = type === 'income' ? '#0E33F3' : '#242D35';

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.7}
      disabled={!onPress}
      style={styles.card}
    >
      <View style={styles.iconContainer}>{categoryIcon}</View>
      <View style={styles.middle}>
        <Text variant="subheading14" color="#242D35" numberOfLines={1}>
          {title}
        </Text>
        <Text variant="body12" color="#6B7580" style={styles.metadata} numberOfLines={1}>
          {metadata}
        </Text>
      </View>
      <Text variant="subheading14" color={amountColor} style={styles.amount}>
        {amount}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#FFFFFF',
    borderRadius: 16,
    padding: 12,
    shadowColor: '#1D3A58',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 32,
    elevation: 8,
  },
  iconContainer: {
    width: 44,
    height: 44,
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  middle: {
    flex: 1,
    marginRight: 8,
  },
  metadata: {
    marginTop: 2,
  },
  amount: {
    flexShrink: 0,
  },
});

export default TransactionItem;
