import React, { useState } from 'react';
import { StyleSheet } from 'react-native';
import { Redirect, useLocalSearchParams, usePreventRemove } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ConfirmDialog from '@components/organisms/ConfirmDialog';
import DeleteTransactionDialog from '@components/organisms/DeleteTransactionDialog';
import TransactionForm from '@components/organisms/TransactionForm';
import ScreenLayout from '@components/templates/ScreenLayout';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useDeleteTransaction } from '@/hooks/useDeleteTransaction';
import { useTransactionForm } from '@/hooks/useTransactionForm';
import { ROUTES } from '@/navigation/routes';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { Transaction } from '@/types/transaction';
import { getTransactionType } from '@/utils/transactions';

const copy = strings.transactions.edit;

const EditForm: React.FC<{ transaction: Transaction }> = ({ transaction }) => {
  const goBack = useGoBack(ROUTES.transactions.list);
  const type = getTransactionType(transaction);
  const [leaving, setLeaving] = useState(false);
  // The navigation that was stopped, to carry on with if the changes are discarded.
  const [blocked, setBlocked] = useState<{ resume: () => void } | null>(null);

  const { fields, changed, invalid, failed, saving, attention, submit } = useTransactionForm({ type, transaction });
  // Catches every way out: Cancel, Android back, iOS swipe and the browser's back.
  const disablePrevention = usePreventRemove(changed && !leaving, ({ repeat }) => setBlocked({ resume: repeat }));

  // Saved or deleted: leave without asking about unsaved changes.
  const leave = () => {
    setLeaving(true);
    setBlocked(null);
    disablePrevention();
    goBack();
  };

  const deletion = useDeleteTransaction(transaction, leave);
  const save = async () => {
    if (await submit()) leave();
  };

  const keepEditing = () => setBlocked(null);
  const discard = () => {
    setLeaving(true);
    setBlocked(null);
    blocked?.resume();
  };

  return (
    <ScreenLayout
      title={copy.title}
      headerLeft={<Button title={copy.cancel} variant="link" size="sm" onPress={goBack} style={styles.cancel} />}
      headerRight={<Button title={copy.save} size="sm" loading={saving} onPress={save} />}
      scrollKey={String(attention)}
      footer={<Button title={copy.delete} variant="dangerLink" disabled={saving} onPress={deletion.ask} />}
    >
      {failed ? (
        <FeedbackBanner tone="error" icon="circle-alert" title={copy.failedTitle} message={copy.failedMessage} />
      ) : null}

      <TransactionForm {...fields} overline={copy.overline[type](transaction.title)} />

      {invalid ? (
        <FeedbackBanner
          tone="error"
          title={copy.failedTitle}
          message={strings.transactions.form.validation.otherFields}
        />
      ) : null}
      <AppText variant="body12" color={colors.text.secondary}>
        {copy.note(transaction.title)}
      </AppText>

      <DeleteTransactionDialog {...deletion.dialog} />
      <ConfirmDialog
        visible={!!blocked}
        title={copy.discardTitle}
        message={copy.discardMessage}
        onDismiss={keepEditing}
        actions={
          <>
            <Button title={copy.discard} variant="dangerLink" onPress={discard} />
            <Button title={copy.keepEditing} onPress={keepEditing} />
          </>
        }
      />
    </ScreenLayout>
  );
};

/** 03-05A / 03-05B / 03-05C · Edit Transaction, with delete and the unsaved-changes guard. */
const EditTransactionScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  // Read once: deleting must not unmount the form before it has navigated back.
  const [transaction] = useState(() => transactionService.getTransaction(id));

  return transaction ? <EditForm transaction={transaction} /> : <Redirect href={ROUTES.transactions.list} />;
};

const styles = StyleSheet.create({
  cancel: { paddingHorizontal: 0 },
});

export default EditTransactionScreen;
