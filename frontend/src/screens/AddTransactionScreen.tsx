import React from 'react';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import SegmentedControl from '@components/atoms/SegmentedControl';
import TabPanel from '@components/atoms/TabPanel';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import TransactionForm from '@components/organisms/TransactionForm';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useTabParam } from '@/hooks/useTabParam';
import { useTransactionForm } from '@/hooks/useTransactionForm';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { dashboardService } from '@/services/dashboardService';
import { transactionService } from '@/services/transactionService';
import { strings } from '@/strings';
import { Transaction, TransactionType } from '@/types/transaction';
import { formatCurrency, formatMonthName, formatMonthYear, parseDate } from '@/utils/formatters';

const shared = strings.transactions;
const copy = shared.form;

const TAB_ORDER = ['expense', 'income'] as const satisfies readonly TransactionType[];
const TAB_OPTIONS = TAB_ORDER.map((value) => ({ value, label: shared.types[value] }));

// Replace, not push: once saved, back never returns to the filled-in form.
const showSaved = ({ id }: Transaction) => router.replace({ pathname: ROUTES.transactions.saved, params: { id } });

const unchangedTotal = (type: TransactionType) => {
  const { totalExpense, totalSalary } = dashboardService.getSummary();
  const total = formatCurrency(type === 'expense' ? totalExpense : totalSalary);
  return copy[type].unchanged(formatMonthName(transactionService.getToday()), total);
};

/**
 * 03-06 / 03-08 / 03-10 / 03-12 / 03-14 · Add Expense and Add Income, one screen with two tabs.
 * Each tab keeps what was typed and its own errors.
 */
const AddTransactionScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.app.home);
  const [type, changeType] = useTabParam(TAB_ORDER);
  const { fields, invalid, failed, saving, attention, submit } = useTransactionForm({ type });

  const save = async () => {
    const saved = await submit();
    if (saved) showSaved(saved);
  };

  const typeCopy = copy[type];
  const { errors, draft } = fields;
  const month = formatMonthYear(parseDate(draft.date) ?? transactionService.getToday());
  // The expense error state drops the context line to bring the message up (03-08).
  const overline = type === 'expense' && errors.amount ? undefined : copy.overline(month);
  const note = failed ? unchangedTotal(type) : !invalid && isMockSource('transactions') ? copy.sampleNote : null;

  return (
    <ScreenLayout
      title={typeCopy.screenTitle}
      onBack={goBack}
      toolbar={<SegmentedControl options={TAB_OPTIONS} value={type} onChange={changeType} />}
      scrollKey={`${type}-${attention}`}
      footer={
        <>
          <Button title={failed ? copy.retry : typeCopy.submit} loading={saving} onPress={save} />
          <Button title={copy.cancel} variant="outline" onPress={goBack} />
        </>
      }
    >
      <TabPanel index={TAB_ORDER.indexOf(type)}>
        {failed ? (
          <FeedbackBanner tone="error" icon="circle-alert" title={typeCopy.notSaved} message={typeCopy.saveFailed} />
        ) : null}

        <TransactionForm {...fields} overline={overline} />

        {invalid ? (
          <FeedbackBanner
            tone="error"
            icon={type === 'income' ? 'circle-alert' : undefined}
            title={typeCopy.notSaved}
            message={errors.amount ? typeCopy.fixAmount : copy.validation.otherFields}
          />
        ) : null}
        {note ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {note}
          </AppText>
        ) : null}
      </TabPanel>
    </ScreenLayout>
  );
};

export default AddTransactionScreen;
