import React from 'react';
import { StyleSheet, View } from 'react-native';
import SectionHeader from '@components/molecules/SectionHeader';
import TransactionItem, { TransactionItemProps } from '@components/molecules/TransactionItem';

export interface RecentTransactionsProps {
  transactions: (TransactionItemProps & { id: string })[];
  onViewAll?: () => void;
}

/**
 * Short, fixed-length preview list rendered inside the parent ScrollView —
 * a nested FlatList would only add overhead for a handful of rows.
 */
const RecentTransactions: React.FC<RecentTransactionsProps> = ({ transactions, onViewAll }) => (
  <View style={styles.container}>
    <SectionHeader title="Recent Transactions" actionLabel="View All" onAction={onViewAll} />
    <View style={styles.list}>
      {transactions.map(({ id, ...item }) => (
        <TransactionItem key={id} {...item} />
      ))}
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: { width: '100%', gap: 16 },
  list: { gap: 12 },
});

export default RecentTransactions;
