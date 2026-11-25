import React, { useMemo } from 'react';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import Chip from '@components/atoms/Chip';
import SegmentedControl from '@components/atoms/SegmentedControl';
import SelectField from '@components/atoms/SelectField';
import TabPanel from '@components/atoms/TabPanel';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import StateSummary from '@components/molecules/StateSummary';
import TransactionHistory from '@components/organisms/TransactionHistory';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useServiceData } from '@/hooks/useServiceData';
import { useTabParam } from '@/hooks/useTabParam';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { TransactionTypeFilter } from '@/types/transaction';
import { formatMonthYear } from '@/utils/formatters';
import { groupByDay } from '@/utils/transactions';

const copy = strings.transactions.list;

const TAB_ORDER = ['all', 'expense', 'income'] as const satisfies readonly TransactionTypeFilter[];
const TAB_OPTIONS = TAB_ORDER.map((value) => ({ value, label: copy.tabs[value] }));

const openSearch = () => router.push(ROUTES.transactions.search);
const openDetails = (id: string) => router.push({ pathname: ROUTES.transactions.details, params: { id } });

/**
 * 03-01 · All Transactions: every record by date, split into All / Expenses / Income.
 * Works like Bank Messages: pinned tabs that switch on touch-down, only the list slides.
 */
const TransactionsScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.app.home);
  const [tab, changeTab] = useTabParam(TAB_ORDER);
  const transactions = useServiceData(transactionService.getTransactions);

  // One list for the three tabs: a switch only shows or hides its cards, so it has nothing to compute.
  const days = useMemo(() => groupByDay(transactions, transactionService.getAccounts()), [transactions]);
  const tabIsEmpty = days.every(
    ({ expenses, income }) => (tab === 'income' || !expenses.length) && (tab === 'expense' || !income.length),
  );

  const isMock = isMockSource('transactions');
  const month = formatMonthYear(transactionService.getToday());

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      toolbar={<SegmentedControl options={TAB_OPTIONS} value={tab} onChange={changeTab} />}
      scrollKey={tab}
      footer={
        <>
          <Button
            title={copy.filters}
            onPress={() => router.push({ pathname: ROUTES.transactions.filters, params: { type: tab } })}
          />
          {/* Insights (section 08) has no screen yet, so this returns to where the list was opened from. */}
          <Button title={copy.backToInsights} variant="outline" onPress={goBack} />
        </>
      }
    >
      <SelectField label={copy.searchLabel} placeholder={copy.searchPlaceholder} icon="search" onPress={openSearch} />
      <Chip label={isMock ? copy.samplePeriod(month) : month} />

      <TabPanel index={TAB_ORDER.indexOf(tab)}>
        {tabIsEmpty ? (
          <Card>
            <StateSummary size="compact" icon="search-x" heading={copy.emptyTitle} description={copy.emptyMessage} />
          </Card>
        ) : (
          <TransactionHistory days={days} show={tab} onSelect={openDetails} />
        )}
      </TabPanel>

      {isMock ? (
        <>
          <FeedbackBanner title={copy.sampleTitle} message={copy.sampleMessage} />
          <AppText variant="body12" color={colors.text.secondary}>
            {copy.sampleFootnote}
          </AppText>
        </>
      ) : null}
    </ScreenLayout>
  );
};

export default TransactionsScreen;
