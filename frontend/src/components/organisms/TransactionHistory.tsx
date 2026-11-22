import React, { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { spacing } from '@theme/index';
import SectionHeader from '@components/molecules/SectionHeader';
import { strings } from '@/strings';
import { TransactionTypeFilter } from '@/types/transaction';
import TransactionGroupCard, { TransactionGroupCardProps } from './TransactionGroupCard';

type Rows = TransactionGroupCardProps['transactions'];

export interface TransactionDay {
  /** ISO calendar date; identifies the section. */
  date: string;
  /** e.g. "28 October 2026" */
  title: string;
  expenses: Rows;
  income: Rows;
}

export interface TransactionHistoryProps {
  /** Keep it stable: switching `show` then re-renders no row at all. */
  days: TransactionDay[];
  /** The other type's cards stay mounted but hidden, so switching is instant however long the list is. */
  show?: TransactionTypeFilter;
  /** Keep it stable, like `days`. */
  onSelect: (id: string) => void;
}

const INCOME_BADGE = { label: strings.transactions.types.income, tone: 'success' } as const;

interface DayCardProps extends Pick<TransactionGroupCardProps, 'badge'> {
  rows: Rows;
  onSelect: TransactionHistoryProps['onSelect'];
}

const DayCard = memo(function DayCard({ rows, badge, onSelect }: DayCardProps) {
  const transactions = rows.map((row) => ({ ...row, onPress: () => onSelect(row.id) }));
  return <TransactionGroupCard badge={badge} transactions={transactions} />;
});

/** Dated transaction cards, used by All Transactions and Search. Income sits on its own badged card. */
const TransactionHistory: React.FC<TransactionHistoryProps> = ({ days, show = 'all', onSelect }) => (
  <>
    {days.map(({ date, title, expenses, income }) => {
      const showExpenses = show !== 'income' && expenses.length > 0;
      const showIncome = show !== 'expense' && income.length > 0;

      return (
        <View key={date} style={showExpenses || showIncome ? styles.day : styles.hidden}>
          <SectionHeader title={title} />
          {expenses.length > 0 ? (
            <View style={!showExpenses && styles.hidden}>
              <DayCard rows={expenses} onSelect={onSelect} />
            </View>
          ) : null}
          {income.length > 0 ? (
            <View style={!showIncome && styles.hidden}>
              <DayCard rows={income} badge={INCOME_BADGE} onSelect={onSelect} />
            </View>
          ) : null}
        </View>
      );
    })}
  </>
);

const styles = StyleSheet.create({
  day: { width: '100%', gap: spacing.xl },
  hidden: { display: 'none' },
});

export default memo(TransactionHistory);
