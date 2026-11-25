import React, { useMemo } from 'react';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ListRow from '@components/molecules/ListRow';
import StateSummary from '@components/molecules/StateSummary';
import TransactionRecordCard from '@components/organisms/TransactionRecordCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useServiceData } from '@/hooks/useServiceData';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { transactionService } from '@/services/transactionService';
import { useTransactionFilterStore } from '@/store/transactionFilterStore';
import { strings } from '@/strings';
import { TransactionFilters } from '@/types/transaction';
import { formatDate, formatDateRange, formatMonthYear } from '@/utils/formatters';
import { filterTransactions, getTransactionType, toTransactionRow } from '@/utils/transactions';

const shared = strings.transactions;
const copy = shared.filtered;

const editFilters = () => router.push(ROUTES.transactions.filters);
const openDetails = (id: string) => router.push({ pathname: ROUTES.transactions.details, params: { id } });

/** With nothing applied (web refresh, cleared), the results are simply the current month. */
const unfiltered = (): TransactionFilters => {
  const today = transactionService.getToday();
  return { from: `${today.slice(0, 7)}-01`, to: today, type: 'all', category: 'all', accountId: 'all' };
};

/** 03-03 / 03-04 · Filtered Transactions: the matching records, or why there are none. */
const FilteredTransactionsScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.transactions.list);
  const applied = useTransactionFilterStore((state) => state.filters);
  const clearFilters = useTransactionFilterStore((state) => state.clearFilters);
  const transactions = useServiceData(transactionService.getTransactions);

  const filters = useMemo(() => applied ?? unfiltered(), [applied]);
  const results = useMemo(() => filterTransactions(transactions, filters), [transactions, filters]);

  const clear = () => {
    clearFilters();
    router.dismissTo(ROUTES.transactions.list);
  };

  const { from, to, type, category, accountId } = filters;
  const isMock = isMockSource('transactions');
  const isEmpty = results.length === 0;
  const accounts = transactionService.getAccounts();
  const account = accounts.find(({ id }) => id === accountId)?.label ?? shared.allAccounts;
  const range = formatDateRange(from, to);
  const month = formatMonthYear(to);
  const summary = [
    category === 'all' ? shared.filters.allCategories : strings.categories[category],
    type === 'all' ? copy.allTypes : shared.types[type],
    isEmpty ? month : null,
  ]
    .filter(Boolean)
    .join(' · ');
  const linked = results.find(({ smsBank, receipt }) => smsBank && receipt);

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        isEmpty ? (
          <>
            <Button title={shared.clearFilters} onPress={clear} />
            <Button title={copy.edit} variant="outline" onPress={editFilters} />
          </>
        ) : (
          <>
            <Button title={copy.edit} onPress={editFilters} />
            <Button title={shared.clearFilters} variant="outline" onPress={clear} />
          </>
        )
      }
    >
      <Chip label={summary} />

      {isEmpty ? (
        <>
          <DividedCard footnote={copy.appliedRange(range)}>
            <ListRow title={shared.account} trailing={account} />
          </DividedCard>
          <StateSummary
            icon="search-x"
            heading={copy.emptyTitle}
            description={isMock ? copy.sampleEmptyMessage : copy.emptyMessage}
          />
          <FeedbackBanner title={copy.safeTitle} message={copy.safeMessage} />
        </>
      ) : (
        <>
          <DividedCard footnote={copy.applied(month)}>
            <ListRow title={copy.dateRange} subtitle={range} trailing={account} />
          </DividedCard>
          <ListRow title={isMock ? copy.sampleMatching : copy.matching} trailing={copy.count(results.length)} />
          {results.map((transaction) => (
            <TransactionRecordCard
              key={transaction.id}
              transaction={{
                ...toTransactionRow(transaction),
                meta: `${shared.types[getTransactionType(transaction)]} · ${formatDate(transaction.date)}`,
              }}
              details={[
                { label: shared.category, value: strings.categories[transaction.category] },
                {
                  label: shared.account,
                  value: accounts.find(({ id }) => id === transaction.accountId)?.shortLabel ?? shared.details.noAccount,
                },
              ]}
              footnote={[transaction.note, transaction.time && shared.details.cairoTime(transaction.time)]
                .filter(Boolean)
                .join(' · ')}
              action={{ label: copy.view, onPress: () => openDetails(transaction.id) }}
            />
          ))}
          {linked ? <FeedbackBanner title={copy.linkedTitle} message={copy.linkedMessage(linked.title)} /> : null}
        </>
      )}
    </ScreenLayout>
  );
};

export default FilteredTransactionsScreen;
