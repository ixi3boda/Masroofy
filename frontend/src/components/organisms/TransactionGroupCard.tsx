import React, { Fragment } from 'react';
import { StyleSheet } from 'react-native';
import Card from '@components/atoms/Card';
import Chip, { ChipTone } from '@components/atoms/Chip';
import Divider from '@components/atoms/Divider';
import TransactionItem, { TransactionItemProps } from '@components/molecules/TransactionItem';

export interface TransactionGroupCardProps {
  transactions: (Omit<TransactionItemProps, 'variant'> & { id: string })[];
  /** Optional badge above the rows, e.g. "Income". */
  badge?: { label: string; tone: ChipTone };
}

/** One card of transaction rows separated by dividers (a day's entries, a saved record…). */
const TransactionGroupCard: React.FC<TransactionGroupCardProps> = ({ transactions, badge }) => (
  <Card style={styles.card}>
    {badge ? <Chip label={badge.label} tone={badge.tone} /> : null}
    {transactions.map(({ id, ...item }, index) => (
      <Fragment key={id}>
        {index > 0 ? <Divider /> : null}
        <TransactionItem {...item} variant="plain" />
      </Fragment>
    ))}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 14 },
});

export default TransactionGroupCard;
