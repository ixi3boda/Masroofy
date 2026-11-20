import React, { ReactNode } from 'react';
import ListRow from '@components/molecules/ListRow';
import DividedCard from '@components/molecules/DividedCard';
import TransactionItem, { TransactionItemProps } from './TransactionItem';

export interface TransactionRecordCardProps {
  transaction: Omit<TransactionItemProps, 'variant' | 'onPress'>;
  /** Key–value lines under the transaction, e.g. Account / Status. */
  details: { label: string; value: string }[];
  /** Above the transaction without a divider, e.g. a match warning banner or status chip. */
  header?: ReactNode;
  footnote?: string;
}

/**
 * Saved/confirmed record summary: one transaction plus its key details —
 * used after saving, SMS matching, voice confirmation and receipt attachment.
 */
const TransactionRecordCard: React.FC<TransactionRecordCardProps> = ({ transaction, details, header, footnote }) => (
  <DividedCard header={header} footnote={footnote}>
    <TransactionItem {...transaction} variant="plain" />
    {details.map((detail) => (
      <ListRow key={detail.label} title={detail.label} trailing={detail.value} />
    ))}
  </DividedCard>
);

export default TransactionRecordCard;
