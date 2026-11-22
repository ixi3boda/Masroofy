import React, { useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { spacing } from '@theme/index';
import Input from '@components/atoms/Input';
import SelectField from '@components/atoms/SelectField';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import { strings } from '@/strings';
import { TransactionDraft, TransactionDraftErrors, TransactionType } from '@/types/transaction';
import AmountEntryCard from './AmountEntryCard';
import OptionList, { OptionListItem } from './OptionList';

const shared = strings.transactions;
const copy = shared.form;

export interface TransactionFormProps {
  type: TransactionType;
  draft: TransactionDraft;
  errors: TransactionDraftErrors;
  accounts: OptionListItem<string>[];
  /** Context line on the amount card, e.g. "Manual entry · October 2026". */
  overline?: string;
  onChange: (changes: Partial<TransactionDraft>) => void;
  onPickCategory: () => void;
}

/** The fields shared by Add Expense, Add Income and Edit Transaction. */
const TransactionForm: React.FC<TransactionFormProps> = ({
  type,
  draft,
  errors,
  accounts,
  overline,
  onChange,
  onPickCategory,
}) => {
  const [accountsOpen, setAccountsOpen] = useState(false);
  const account = accounts.find(({ value }) => value === draft.accountId);

  const chooseAccount = (accountId: string) => {
    onChange({ accountId });
    setAccountsOpen(false);
  };

  return (
    <>
      <AmountEntryCard
        overline={overline}
        label={errors.amount ? copy.amountRequired : copy.amount}
        value={draft.amount}
        onChangeText={(amount) => onChange({ amount })}
        errorMessage={errors.amount}
        errorDisplay={type === 'expense' ? 'banner' : 'inline'}
      />
      <View style={styles.fields}>
        <Input
          label={copy[type].title}
          value={draft.title}
          onChangeText={(title) => onChange({ title })}
          hasError={!!errors.title}
          errorMessage={errors.title}
        />
        <SelectField
          label={shared.category}
          value={draft.category ? strings.categories[draft.category] : undefined}
          placeholder={copy.categoryPlaceholder}
          onPress={onPickCategory}
          hasError={!!errors.category}
        />
        {errors.category ? <FeedbackBanner tone="error" title={errors.category} /> : null}
        <Input
          label={copy.date}
          placeholder={copy.datePlaceholder}
          value={draft.date}
          onChangeText={(date) => onChange({ date })}
          hasError={!!errors.date}
          errorMessage={errors.date}
        />
        <SelectField
          label={shared.account}
          value={account?.title}
          placeholder={copy.accountPlaceholder}
          onPress={() => setAccountsOpen((open) => !open)}
          hasError={!!errors.accountId}
        />
        {accountsOpen ? <OptionList options={accounts} value={draft.accountId} onChange={chooseAccount} /> : null}
        {errors.accountId ? <FeedbackBanner tone="error" title={errors.accountId} /> : null}
        <Input label={copy.notes} value={draft.note} onChangeText={(note) => onChange({ note })} />
      </View>
    </>
  );
};

const styles = StyleSheet.create({
  fields: { width: '100%', gap: spacing.lg },
});

export default TransactionForm;
