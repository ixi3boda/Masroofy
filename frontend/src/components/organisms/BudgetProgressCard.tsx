import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import ProgressBar from '@components/atoms/ProgressBar';
import { formatCurrency } from '@/utils/formatters';

export interface BudgetProgressCardProps {
  spent: number;
  limit: number;
  /** e.g. "Oct 2026" */
  periodLabel: string;
}

const BudgetProgressCard: React.FC<BudgetProgressCardProps> = ({ spent, limit, periodLabel }) => {
  const progress = limit > 0 ? spent / limit : 0;
  const remaining = Math.max(limit - spent, 0);

  return (
    <Card style={styles.card}>
      <View style={styles.row}>
        <AppText variant="subheading16">Budget Progress</AppText>
        <AppText variant="subheading16" color={colors.primary}>
          {Math.round(progress * 100)}% Used
        </AppText>
      </View>
      <View style={styles.details}>
        <View style={styles.row}>
          <AppText variant="body14" color={colors.text.secondary}>
            Remaining Allowance
          </AppText>
          <AppText variant="body14">{formatCurrency(remaining)}</AppText>
        </View>
        <ProgressBar progress={progress} />
        <AppText variant="body12" color={colors.text.secondary}>
          {periodLabel} • Budget {formatCurrency(limit)}
        </AppText>
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { gap: 16 },
  row: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: 8 },
  details: { gap: 8 },
});

export default BudgetProgressCard;
