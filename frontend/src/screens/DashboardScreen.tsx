import React from 'react';
import { spacing } from '@theme/index';
import IconButton from '@components/atoms/IconButton';
import { ActionChipProps } from '@components/molecules/ActionChip';
import { QuickActionTileProps } from '@components/molecules/QuickActionTile';
import ActionChipGroup from '@components/organisms/ActionChipGroup';
import BottomTabBar from '@components/organisms/BottomTabBar';
import BudgetProgressCard from '@components/organisms/BudgetProgressCard';
import IncomeExpenseChartCard from '@components/organisms/IncomeExpenseChartCard';
import QuickActionsGrid from '@components/organisms/QuickActionsGrid';
import RecentTransactions from '@components/organisms/RecentTransactions';
import StatCardRow from '@components/organisms/StatCardRow';
import ScreenLayout from '@components/templates/ScreenLayout';
import { CATEGORY_LABELS } from '@/constants/transactions';
import { mockDashboardSummary } from '@/services/mockDashboardService';
import { formatCurrency, formatDayMonth, formatSignedCurrency } from '@/utils/formatters';

const MORE_ACTIONS: ActionChipProps[] = [
  { label: 'Savings', icon: 'piggy-bank', variant: 'brand' },
  { label: 'Reminders', icon: 'bell' },
  { label: 'Insights', icon: 'chart-column' },
  { label: 'Budgets', icon: 'wallet' },
  { label: 'Markets', icon: 'trending-up' },
  { label: 'Accounts', icon: 'landmark' },
  { label: 'Salary Setup', icon: 'salary' },
];

const QUICK_ACTIONS: QuickActionTileProps[] = [
  { label: 'Add Transaction', icon: 'plus' },
  { label: 'SMS Detection', icon: 'sms', hasAlert: true },
  { label: 'Scan Receipt', icon: 'scan' },
  { label: 'Voice Entry', icon: 'mic' },
];

const DashboardScreen: React.FC = () => {
  const {
    periodLabel,
    totalSalary,
    totalExpense,
    budgetLimit,
    primaryAccount,
    cashBalance,
    recentTransactions,
  } = mockDashboardSummary;

  const transactions = recentTransactions.map(({ id, merchant, category, date, amount }) => ({
    id,
    title: merchant,
    meta: `${CATEGORY_LABELS[category]} • ${formatDayMonth(date)}`,
    amount: formatSignedCurrency(amount),
    icon: category,
  }));

  return (
    <ScreenLayout
      title="Masroofy Home"
      titleAlign="start"
      gap={spacing.xxl}
      headerRight={<IconButton name="user" accessibilityLabel="Profile" />}
      bottomBar={<BottomTabBar activeTab="home" />}
    >
      <StatCardRow
        items={[
          { label: 'Total Salary', value: formatCurrency(totalSalary), icon: 'wallet' },
          { label: 'Total Expense', value: formatCurrency(totalExpense), icon: 'wallet', variant: 'brand' },
        ]}
      />
      <ActionChipGroup title="More Actions" actions={MORE_ACTIONS} />
      <QuickActionsGrid title="Quick Actions" actions={QUICK_ACTIONS} />
      <StatCardRow
        items={[
          {
            label: 'Current Balance',
            value: formatCurrency(primaryAccount.balance + cashBalance),
            variant: 'brand',
          },
          {
            label: primaryAccount.name,
            value: formatCurrency(primaryAccount.balance),
            caption: `Cash · ${formatCurrency(cashBalance)}`,
          },
        ]}
      />
      <BudgetProgressCard spent={totalExpense} limit={budgetLimit} periodLabel={periodLabel} />
      <IncomeExpenseChartCard income={totalSalary} expense={totalExpense} periodLabel={periodLabel} />
      <RecentTransactions transactions={transactions} />
    </ScreenLayout>
  );
};

export default DashboardScreen;
