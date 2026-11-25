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
import { CATEGORY_ICONS } from '@/constants/categories';
import { whenOpen } from '@/constants/features';
import { useServiceData } from '@/hooks/useServiceData';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { dashboardService } from '@/services/dashboardService';
import { smsService } from '@/services/smsService';
import { strings } from '@/strings';
import { formatCurrency, formatDayMonth, formatSignedCurrency } from '@/utils/formatters';

const copy = strings.dashboard;

const MORE_ACTIONS: ActionChipProps[] = [
  { label: copy.moreActions.savings, icon: 'piggy-bank', variant: 'brand' },
  { label: copy.moreActions.reminders, icon: 'bell' },
  { label: copy.moreActions.insights, icon: 'chart-column' },
  { label: copy.moreActions.budgets, icon: 'wallet' },
  { label: copy.moreActions.markets, icon: 'trending-up' },
  { label: copy.moreActions.accounts, icon: 'landmark' },
  { label: copy.moreActions.salarySetup, icon: 'salary' },
];

const openAdd = whenOpen('addTransaction', () => router.push(ROUTES.transactions.add));
const openTransactions = whenOpen('transactions', () => router.push(ROUTES.transactions.list));
const openSms = whenOpen('sms', () => router.push(ROUTES.sms.messages));

/** The SMS tile shows a dot while bank messages are waiting for review. */
const quickActions = (hasNewSms: boolean): QuickActionTileProps[] => [
  { label: copy.quickActions.addTransaction, icon: 'plus', onPress: openAdd },
  { label: copy.quickActions.smsDetection, icon: 'sms', hasAlert: hasNewSms, onPress: openSms },
  { label: copy.quickActions.scanReceipt, icon: 'scan' },
  { label: copy.quickActions.voiceEntry, icon: 'mic' },
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
  } = useServiceData(dashboardService.getSummary);
  const smsMessages = useServiceData(smsService.getMessages);
  const hasNewSms = smsMessages.some((message) => message.status === 'new');

  const transactions = recentTransactions.map(({ id, title, category, date, amount }) => ({
    id,
    title,
    meta: `${strings.categories[category]} • ${formatDayMonth(date)}`,
    amount: formatSignedCurrency(amount),
    icon: CATEGORY_ICONS[category],
    onPress: whenOpen('transactions', () => router.push({ pathname: ROUTES.transactions.details, params: { id } })),
  }));

  return (
    <ScreenLayout
      title={copy.title}
      titleAlign="start"
      gap={spacing.xxl}
      headerRight={<IconButton name="user" accessibilityLabel={strings.common.a11y.profile} />}
      bottomBar={<BottomTabBar activeTab="home" onAddPress={openAdd} />}
    >
      <StatCardRow
        items={[
          { label: copy.totalSalary, value: formatCurrency(totalSalary), icon: 'wallet' },
          { label: copy.totalExpense, value: formatCurrency(totalExpense), icon: 'wallet', variant: 'brand' },
        ]}
      />
      <ActionChipGroup title={copy.moreActions.title} actions={MORE_ACTIONS} />
      <QuickActionsGrid title={copy.quickActions.title} actions={quickActions(hasNewSms)} />
      <StatCardRow
        items={[
          {
            label: copy.currentBalance,
            value: formatCurrency(primaryAccount.balance + cashBalance),
            variant: 'brand',
          },
          {
            label: primaryAccount.name,
            value: formatCurrency(primaryAccount.balance),
            caption: copy.cashBalance(formatCurrency(cashBalance)),
          },
        ]}
      />
      <BudgetProgressCard spent={totalExpense} limit={budgetLimit} periodLabel={periodLabel} />
      <IncomeExpenseChartCard income={totalSalary} expense={totalExpense} periodLabel={periodLabel} />
      <RecentTransactions transactions={transactions} onViewAll={openTransactions} />
    </ScreenLayout>
  );
};

export default DashboardScreen;
