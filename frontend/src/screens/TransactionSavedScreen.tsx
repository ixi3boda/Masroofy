import React from 'react';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import Button from '@components/atoms/Button';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import StateSummary from '@components/molecules/StateSummary';
import TransactionRecordCard from '@components/organisms/TransactionRecordCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { dashboardService } from '@/services/dashboardService';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { formatCurrency, formatDate, formatMonthName } from '@/utils/formatters';
import { getTransactionType, toTransactionRow } from '@/utils/transactions';

const shared = strings.transactions;
const copy = shared.saved;

const goHome = () => router.dismissTo(ROUTES.app.home);

/** 03-09 / 03-13 · Transaction Saved and Income Saved. */
const TransactionSavedScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const goBack = useGoBack(ROUTES.app.home);
  const transaction = transactionService.getTransaction(id);

  if (!transaction) return <Redirect href={ROUTES.transactions.list} />;

  const { title, category, date, accountId } = transaction;
  const type = getTransactionType(transaction);
  const typeCopy = copy[type];
  const month = formatMonthName(date);
  const amount = formatCurrency(Math.abs(transaction.amount));
  const account = transactionService.getAccounts().find((candidate) => candidate.id === accountId);

  // Home only totals the current month.
  const isThisMonth = date.slice(0, 7) === transactionService.getToday().slice(0, 7);
  const { totalExpense, totalSalary } = dashboardService.getSummary();
  const total = formatCurrency(type === 'expense' ? totalExpense : totalSalary);

  return (
    <ScreenLayout
      title={typeCopy.screenTitle}
      onBack={goBack}
      footer={
        <>
          <Button title={typeCopy.done} onPress={goHome} />
          <Button
            title={typeCopy.another}
            variant="outline"
            onPress={() => router.replace({ pathname: ROUTES.transactions.add, params: { tab: type } })}
          />
        </>
      }
    >
      <StateSummary icon="check" heading={typeCopy.heading} description={typeCopy.description(title, month)} />

      <TransactionRecordCard
        transaction={{
          ...toTransactionRow(transaction),
          amount,
          meta: copy.meta(strings.categories[category], formatDate(date)),
        }}
        details={[
          { label: shared.account, value: account?.shortLabel ?? shared.details.noAccount },
          { label: copy.status, value: shared.recorded },
        ]}
        footnote={isThisMonth ? typeCopy.included(month, total) : undefined}
      />

      <FeedbackBanner tone="success" title={typeCopy.onceTitle} message={typeCopy.onceMessage(amount, title)} />
    </ScreenLayout>
  );
};

export default TransactionSavedScreen;
