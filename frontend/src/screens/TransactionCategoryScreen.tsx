import React, { useState } from 'react';
import { useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import OptionList from '@components/organisms/OptionList';
import ScreenLayout from '@components/templates/ScreenLayout';
import { CATEGORIES, CATEGORY_ICONS } from '@/constants/categories';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useTransactionDraft } from '@/hooks/useTransactionDraft';
import { ROUTES } from '@/navigation/routes';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { TransactionType } from '@/types/transaction';
import { formatCurrency } from '@/utils/formatters';
import { parseAmount } from '@/utils/validators';

const copy = strings.transactions.categoryPicker;

/** 03-07 / 03-11 · Choose Category: writes to the form's draft only on Done. */
const TransactionCategoryScreen: React.FC = () => {
  const params = useLocalSearchParams<{ type?: string; id?: string }>();
  const type: TransactionType = params.type === 'income' ? 'income' : 'expense';
  const goBack = useGoBack(ROUTES.transactions.add);
  const [transaction] = useState(() => (params.id ? transactionService.getTransaction(params.id) : undefined));
  const { draft, update } = useTransactionDraft(type, transaction);
  const [category, setCategory] = useState(draft.category);

  const isExpense = type === 'expense';
  const options = CATEGORIES[type].map((value) => ({
    value,
    title: strings.categories[value],
    icon: isExpense ? CATEGORY_ICONS[value] : undefined,
  }));

  const amount = parseAmount(draft.amount);
  const title = draft.title.trim();
  const account = transactionService.getAccounts().find(({ id }) => id === draft.accountId)?.shortLabel;
  const retained =
    !isExpense && amount !== null && title
      ? [formatCurrency(amount), draft.date, account].filter(Boolean).join(' · ')
      : null;

  const done = () => {
    update({ category });
    goBack();
  };

  return (
    <ScreenLayout
      title={copy[type].title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.done} disabled={!category} onPress={done} />
          <Button title={copy.cancel} variant="outline" onPress={goBack} />
        </>
      }
    >
      <AppText variant="body14" color={colors.text.secondary}>
        {copy[type].intro}
      </AppText>
      <OptionList options={options} value={category} onChange={setCategory} />
      {retained ? (
        <FeedbackBanner
          title={copy.retainedTitle(title)}
          message={transaction ? copy.existingIncome(retained) : copy.newIncome(retained)}
        />
      ) : null}
    </ScreenLayout>
  );
};

export default TransactionCategoryScreen;
