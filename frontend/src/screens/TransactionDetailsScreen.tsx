import React, { useCallback } from 'react';
import { StyleSheet, View } from 'react-native';
import { router, useFocusEffect, useLocalSearchParams } from 'expo-router';
import { colors, spacing } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import Chip from '@components/atoms/Chip';
import IconTile from '@components/atoms/IconTile';
import AmountSummaryCard from '@components/molecules/AmountSummaryCard';

import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ListRow from '@components/molecules/ListRow';
import ReceiptPreview from '@components/molecules/ReceiptPreview';
import DetailList from '@components/organisms/DetailList';
import DeleteTransactionDialog from '@components/organisms/DeleteTransactionDialog';
import ScreenLayout from '@components/templates/ScreenLayout';
import { CATEGORY_ICONS } from '@/constants/categories';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useDeleteTransaction } from '@/hooks/useDeleteTransaction';
import { useServiceData } from '@/hooks/useServiceData';
import { ROUTES } from '@/navigation/routes';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { Transaction, TransactionReceipt } from '@/types/transaction';
import { formatCurrency, formatDate, formatExactNumber, formatMonthName } from '@/utils/formatters';
import { getTransactionType } from '@/utils/transactions';

const shared = strings.transactions;
const copy = shared.details;

const goHome = () => router.dismissTo(ROUTES.app.home);

const AttachedReceipt: React.FC<{ receipt: TransactionReceipt }> = ({ receipt }) => (
  <Card>
    <ListRow title={copy.receiptTitle} subtitle={copy.receiptSummary(receipt.merchant, formatCurrency(receipt.total))} />
    <ReceiptPreview
      merchant={receipt.merchant}
      subtitle={receipt.subtitle}
      date={formatDate(receipt.date)}
      time={receipt.time}
      totalLabel={copy.receiptTotal}
      total={formatExactNumber(receipt.total)}
      footnote={receipt.footnote}
    />
    <Chip label={copy.receiptChip} tone="success" />
  </Card>
);

interface DetailsProps {
  transaction: Transaction;
  goBack: () => void;
}

const Details: React.FC<DetailsProps> = ({ transaction, goBack }) => {
  const { id, title, category, date, time, amount, accountId, note, smsBank, receipt } = transaction;
  const type = getTransactionType(transaction);
  const deletion = useDeleteTransaction(transaction, goBack);
  const account = transactionService.getAccounts().find((candidate) => candidate.id === accountId);

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <>
          <Button
            title={copy.edit}
            onPress={() => router.push({ pathname: ROUTES.transactions.edit, params: { id } })}
          />
          <Button title={copy.delete} variant="dangerLink" onPress={deletion.ask} />
          <Button title={copy.backHome} variant="outline" onPress={goHome} />
        </>
      }
    >
      <AmountSummaryCard
        header={
          <ListRow
            leading={<IconTile name={CATEGORY_ICONS[category]} />}
            title={title}
            titleVariant="subheading18"
            subtitle={copy.subtitle(strings.categories[category], shared.types[type])}
            trailing={<Chip label={shared.recorded} tone="success" style={styles.status} />}
          />
        }
        amount={formatCurrency(Math.abs(amount))}
        amountVariant="display34"
        caption={copy.included[type](formatMonthName(date))}
      />

      <DividedCard>
        <ListRow
          title={copy.dateTime}
          subtitle={[formatDate(date), time && copy.cairoTime(time)].filter(Boolean).join(' · ')}
        />
        <DetailList
          details={[
            { label: shared.account, value: account?.label ?? copy.noAccount },
            { label: shared.category, value: strings.categories[category] },
            { label: copy.recordedVia, value: smsBank ? copy.sources.sms : copy.sources.manual },
          ]}
        />
        {note ? (
          <View style={styles.note}>
            <AppText variant="overline12" color={colors.text.secondary}>
              {copy.note}
            </AppText>
            <AppText variant="body14">{note}</AppText>
          </View>
        ) : null}
      </DividedCard>

      {receipt ? <AttachedReceipt receipt={receipt} /> : null}
      {smsBank && receipt ? (
        <FeedbackBanner icon="link" title={copy.linkedTitle} message={copy.linkedMessage(smsBank)} />
      ) : null}

      <DeleteTransactionDialog {...deletion.dialog} />
    </ScreenLayout>
  );
};

/** 03-05 / 03-05B · Transaction Details. Steps back by itself when the record no longer exists. */
const TransactionDetailsScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const goBack = useGoBack(ROUTES.transactions.list);
  const transaction = useServiceData(useCallback(() => transactionService.getTransaction(id), [id]));

  useFocusEffect(
    useCallback(() => {
      if (!transactionService.getTransaction(id)) goBack();
    }, [id, goBack]),
  );

  return transaction ? <Details transaction={transaction} goBack={goBack} /> : null;
};

const styles = StyleSheet.create({
  status: { alignSelf: 'center' },
  note: { gap: spacing.md },
});

export default TransactionDetailsScreen;
