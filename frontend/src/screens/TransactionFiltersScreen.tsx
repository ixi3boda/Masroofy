import React, { useState } from 'react';
import { StyleSheet } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import SegmentedControl from '@components/atoms/SegmentedControl';
import DateRangeCard from '@components/molecules/DateRangeCard';
import SectionHeader from '@components/molecules/SectionHeader';
import OptionList from '@components/organisms/OptionList';
import ScreenLayout from '@components/templates/ScreenLayout';
import { CATEGORIES } from '@/constants/categories';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { transactionService } from '@/services/transactionService';
import { useTransactionFilterStore } from '@/store/transactionFilterStore';
import { strings } from '@/strings';
import { TransactionFilters, TransactionTypeFilter } from '@/types/transaction';
import { formatDate, parseDate } from '@/utils/formatters';

const shared = strings.transactions;
const copy = shared.filters;

const TYPES = ['all', 'expense', 'income'] as const satisfies readonly TransactionTypeFilter[];
const TYPE_OPTIONS = TYPES.map((value) => ({ value, label: shared.types[value] }));

/** 03-02 · Filter Transactions: date range, type, category and account. Nothing changes until Apply. */
const TransactionFiltersScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.transactions.list);
  const params = useLocalSearchParams<{ type?: string }>();
  const { filters, applyFilters, clearFilters } = useTransactionFilterStore();
  const today = transactionService.getToday();

  const [from, setFrom] = useState(() => formatDate(filters?.from ?? `${today.slice(0, 7)}-01`));
  const [to, setTo] = useState(() => formatDate(filters?.to ?? today));
  const [type, setType] = useState<TransactionTypeFilter>(
    () => filters?.type ?? TYPES.find((value) => value === params.type) ?? 'all',
  );
  const [category, setCategory] = useState<TransactionFilters['category']>(filters?.category ?? 'all');
  const [accountId, setAccountId] = useState(filters?.accountId ?? 'all');
  const [showAllCategories, setShowAllCategories] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const fromDate = parseDate(from);
  const toDate = parseDate(to);
  const rangeReversed = !!fromDate && !!toDate && fromDate > toDate;

  // Collapsed, the list is the chosen (or first) category + All, as in the design; the rest are one tap away.
  const available = type === 'all' ? [...CATEGORIES.expense, ...CATEGORIES.income] : CATEGORIES[type];
  const featured = category === 'all' ? available[0] : category;
  const others = available.filter((value) => value !== featured);
  const toOption = (value: TransactionFilters['category']) => ({
    value,
    title: value === 'all' ? copy.allCategories : strings.categories[value],
  });
  const categoryOptions = showAllCategories
    ? ['all' as const, ...new Set([featured, ...available])].map(toOption)
    : [featured, 'all' as const].map(toOption);

  const chooseCategory = (value: TransactionFilters['category']) => {
    setCategory(value);
    setShowAllCategories(false);
  };

  const apply = () => {
    setSubmitted(true);
    if (!fromDate || !toDate || rangeReversed) return;
    applyFilters({ from: fromDate, to: toDate, type, category, accountId });
    // Returns to the results when editing them, otherwise takes this form's place.
    router.dismissTo(ROUTES.transactions.filtered);
  };

  const clear = () => {
    clearFilters();
    router.dismissTo(ROUTES.transactions.list);
  };

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.apply} onPress={apply} />
          <Button title={shared.clearFilters} variant="outline" onPress={clear} />
        </>
      }
    >
      <AppText variant="body14" color={colors.text.secondary}>
        {copy.intro}
      </AppText>

      <DateRangeCard
        from={from}
        to={to}
        onChangeFrom={setFrom}
        onChangeTo={setTo}
        fromError={submitted && !fromDate ? copy.dateError : undefined}
        toError={submitted ? (!toDate ? copy.dateError : rangeReversed ? copy.rangeError : undefined) : undefined}
      />

      <SectionHeader title={copy.typeHeading} />
      <SegmentedControl options={TYPE_OPTIONS} value={type} onChange={setType} scrollable />

      <SectionHeader title={shared.category} />
      <OptionList options={categoryOptions} value={category} onChange={chooseCategory} />
      {showAllCategories ? null : (
        <>
          <AppText variant="body12" color={colors.text.secondary}>
            {copy.otherCategories(others.map((value) => strings.categories[value]))}
          </AppText>
          <Button
            title={copy.showCategories}
            variant="link"
            size="sm"
            onPress={() => setShowAllCategories(true)}
            style={styles.showCategories}
          />
        </>
      )}

      <SectionHeader title={shared.account} />
      <OptionList
        options={[
          { value: 'all', title: shared.allAccounts },
          ...transactionService.getAccounts().map(({ id, label }) => ({ value: id, title: label })),
        ]}
        value={accountId}
        onChange={setAccountId}
      />
    </ScreenLayout>
  );
};

const styles = StyleSheet.create({
  showCategories: { paddingHorizontal: 0 },
});

export default TransactionFiltersScreen;
