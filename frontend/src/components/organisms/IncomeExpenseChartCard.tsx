import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import BarChartColumn from '@components/molecules/BarChartColumn';
import { formatNumber } from '@/utils/formatters';

const MAX_BAR_HEIGHT = 120;

export interface IncomeExpenseChartCardProps {
  income: number;
  expense: number;
  /** e.g. "Oct 2026" */
  periodLabel: string;
}

const IncomeExpenseChartCard: React.FC<IncomeExpenseChartCardProps> = ({ income, expense, periodLabel }) => {
  const peak = Math.max(income, expense, 1);
  const barHeight = (value: number) => (value / peak) * MAX_BAR_HEIGHT;

  return (
    <Card style={styles.card}>
      <AppText variant="subheading16">Income vs Expenses</AppText>
      <View style={styles.bars}>
        <BarChartColumn label="Income" value={formatNumber(income)} height={barHeight(income)} />
        <BarChartColumn label="Expenses" value={formatNumber(expense)} height={barHeight(expense)} tone="muted" />
      </View>
      <AppText variant="body12" color={colors.text.secondary}>
        {periodLabel} • Income vs Expenses
      </AppText>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { gap: 20 },
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: 20 },
});

export default IncomeExpenseChartCard;
