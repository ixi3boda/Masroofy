import React, { useCallback, useMemo, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { colors, spacing } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import Icon from '@components/atoms/Icon';
import Input from '@components/atoms/Input';
import RecentSearchItem from '@components/molecules/RecentSearchItem';
import SectionHeader from '@components/molecules/SectionHeader';
import StateSummary from '@components/molecules/StateSummary';
import TransactionHistory from '@components/organisms/TransactionHistory';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useServiceData } from '@/hooks/useServiceData';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { groupByDay, searchTransactions } from '@/utils/transactions';

const copy = strings.transactions.search;

const backToList = () => router.dismissTo(ROUTES.transactions.list);

/** 03-17 · Search: recent searches until something is typed, then live results. */
const TransactionSearchScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.transactions.list);
  const transactions = useServiceData(transactionService.getTransactions);
  const recent = useServiceData(transactionService.getRecentSearches);
  const [query, setQuery] = useState('');

  const term = query.trim();
  const results = useMemo(() => searchTransactions(transactions, term), [transactions, term]);
  const days = useMemo(() => groupByDay(results, transactionService.getAccounts()), [results]);

  const openResult = useCallback(
    (id: string) => {
      transactionService.addRecentSearch(term);
      router.push({ pathname: ROUTES.transactions.details, params: { id } });
    },
    [term],
  );

  const rememberSearch = () => {
    if (results.length > 0) transactionService.addRecentSearch(term);
  };

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={<Button title={copy.back} variant="outline" onPress={backToList} />}
    >
      <Input
        placeholder={copy.placeholder}
        leftIcon={<Icon name="search" />}
        value={query}
        onChangeText={setQuery}
        returnKeyType="search"
        onSubmitEditing={rememberSearch}
        autoFocus
      />
      <Button title={copy.clear} variant="outline" onPress={() => setQuery('')} />

      {term ? (
        <>
          <SectionHeader title={copy.results} trailingText={strings.transactions.filtered.count(results.length)} />
          {results.length > 0 ? (
            <TransactionHistory days={days} onSelect={openResult} />
          ) : (
            <Card>
              <StateSummary size="compact" icon="search-x" heading={copy.emptyTitle} description={copy.emptyMessage} />
            </Card>
          )}
        </>
      ) : (
        <View style={styles.recent}>
          <SectionHeader title={copy.recent} />
          <View style={styles.list}>
            {recent.map((item) => (
              <RecentSearchItem key={item} query={item} onPress={() => setQuery(item)} />
            ))}
          </View>
          {isMockSource('transactions') ? (
            <AppText variant="body12" color={colors.text.secondary}>
              {copy.sampleNote}
            </AppText>
          ) : null}
        </View>
      )}
    </ScreenLayout>
  );
};

const styles = StyleSheet.create({
  recent: { gap: spacing.md },
  list: { gap: spacing.sm },
});

export default TransactionSearchScreen;
