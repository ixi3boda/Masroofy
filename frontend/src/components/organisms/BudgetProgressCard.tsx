import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import ProgressSummary from '@components/molecules/ProgressSummary';
import { formatCurrency } from '@/utils/formatters';

export interface BudgetProgressCardProps {
  spent: number;
  limit: number;
  /** e.g. "Oct 2026" */
  periodLabel: string;
}

/** Home dashboard budget snapshot. */
const BudgetProgressCard: React.FC<BudgetProgressCardProps> = ({ spent, limit, periodLabel }) => {
  const progress = limit > 0 ? spent / limit : 0;

  return (
    <Card style={styles.card}>
      <View style={styles.header}>
        <AppText variant="subheading16">Budget Progress</AppText>
        <AppText variant="subheading16" color={colors.primary}>
          {Math.round(progress * 100)}% Used
        </AppText>
      </View>
      <ProgressSummary
        emphasis="subtle"
        label="Remaining Allowance"
        value={formatCurrency(Math.max(limit - spent, 0))}
        progress={progress}
        tone={progress >= 1 ? 'danger' : 'brand'}
        caption={`${periodLabel} • Budget ${formatCurrency(limit)}`}
      />
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { gap: 16 },
  header: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
});

export default BudgetProgressCard;
