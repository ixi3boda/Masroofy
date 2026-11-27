import React from 'react';
import Chip, { ChipTone } from '@components/atoms/Chip';
import DividedCard from '@components/molecules/DividedCard';
import TransactionItem, { TransactionItemProps } from './TransactionItem';

export interface TransactionGroupCardProps {
  transactions: (Omit<TransactionItemProps, 'variant'> & { id: string })[];
  /** Optional badge above the rows, e.g. "Income". */
  badge?: { label: string; tone: ChipTone };
}

/** One card of transaction rows separated by dividers (a day's entries). */
const TransactionGroupCard: React.FC<TransactionGroupCardProps> = ({ transactions, badge }) => (
  <DividedCard header={badge ? <Chip label={badge.label} tone={badge.tone} /> : undefined}>
    {transactions.map(({ id, ...item }) => (
      <TransactionItem key={id} {...item} variant="plain" />
    ))}
  </DividedCard>
);

export default TransactionGroupCard;
