import React, { ReactNode } from 'react';
import Button from '@components/atoms/Button';
import DividedCard from '@components/molecules/DividedCard';
import DetailList from './DetailList';
import TransactionItem, { TransactionItemProps } from './TransactionItem';

export interface TransactionRecordCardProps {
  transaction: Omit<TransactionItemProps, 'variant' | 'onPress'>;
  /** Key–value lines under the transaction, e.g. Account / Status. */
  details: { label: string; value: string }[];
  /** Above the transaction without a divider, e.g. a match warning banner or status chip. */
  header?: ReactNode;
  footnote?: string;
  /** Outline button closing the card, e.g. "View transaction". */
  action?: { label: string; onPress: () => void };
}

/**
 * Saved/confirmed record summary: one transaction plus its key details —
 * used after saving, SMS matching, voice confirmation and receipt attachment.
 */
const TransactionRecordCard: React.FC<TransactionRecordCardProps> = ({ transaction, details, header, footnote, action }) => (
  <DividedCard
    header={header}
    footnote={footnote}
    action={action ? <Button title={action.label} variant="outline" onPress={action.onPress} /> : undefined}
  >
    <TransactionItem {...transaction} variant="plain" />
    <DetailList details={details} />
  </DividedCard>
);

export default TransactionRecordCard;
