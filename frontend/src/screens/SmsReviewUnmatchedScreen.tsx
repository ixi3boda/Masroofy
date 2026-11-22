import React, { useState } from 'react';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import Input from '@components/atoms/Input';
import SelectField from '@components/atoms/SelectField';
import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import OptionCard from '@components/molecules/OptionCard';
import SectionHeader from '@components/molecules/SectionHeader';
import OptionList, { OptionListItem } from '@components/organisms/OptionList';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { CATEGORIES, CATEGORY_ICONS } from '@/constants/categories';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { smsService } from '@/services/smsService';
import { useSmsReviewStore } from '@/store/smsReviewStore';
import { strings } from '@/strings';
import { TransactionCategory } from '@/types/transaction';
import { formatCurrency, formatDateTime } from '@/utils/formatters';
import { parseAmount } from '@/utils/validators';

const review = strings.sms.review;
const copy = review.unmatched;

const CATEGORY_OPTIONS: OptionListItem<TransactionCategory>[] = CATEGORIES.expense.map((category) => ({
  value: category,
  title: strings.categories[category],
  icon: CATEGORY_ICONS[category],
}));

type Picker = 'category' | 'account';

/** 04-06 · Review Bank SMS: no matching record, so the user verifies every field and the account. */
const SmsReviewUnmatchedScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const message = smsService.getMessage(id);
  const goBack = useGoBack(ROUTES.sms.messages);
  const setDraft = useSmsReviewStore((state) => state.setDraft);
  const accounts = smsService.getTrackingAccounts();

  const [amount, setAmount] = useState(() => (message ? String(message.amount) : ''));
  const [merchant, setMerchant] = useState(message?.merchant ?? '');
  const [dateTime, setDateTime] = useState(() => (message ? formatDateTime(message.receivedAt) : ''));
  const [category, setCategory] = useState<TransactionCategory | null>(message?.suggestedCategory ?? null);
  const [categoryConfirmed, setCategoryConfirmed] = useState(false);
  const [accountId, setAccountId] = useState<string | null>(null);
  const [detailsChecked, setDetailsChecked] = useState(false);
  const [accountChecked, setAccountChecked] = useState(false);
  const [openPicker, setOpenPicker] = useState<Picker | null>(null);
  const [submitted, setSubmitted] = useState(false);

  if (!message) return <Redirect href={ROUTES.sms.messages} />;

  const account = accounts.find((candidate) => candidate.id === accountId);
  const parsedAmount = parseAmount(amount);
  const source = message.cardLast4 ? review.cardSource(message.cardLast4) : message.bank;
  const invalid = {
    amount: parsedAmount === null,
    merchant: !merchant.trim(),
    dateTime: !dateTime.trim(),
    category: category === null,
    account: !account,
    checks: !detailsChecked || !accountChecked,
  };
  const showError = (field: keyof typeof invalid) => submitted && invalid[field];

  const togglePicker = (picker: Picker) => setOpenPicker((current) => (current === picker ? null : picker));

  const chooseCategory = (value: TransactionCategory) => {
    setCategory(value);
    setCategoryConfirmed(true);
    setOpenPicker(null);
  };

  const chooseAccount = (value: string) => {
    setAccountId(value);
    setOpenPicker(null);
  };

  const submit = () => {
    setSubmitted(true);
    if (Object.values(invalid).some(Boolean) || parsedAmount === null || !category || !account) return;
    setDraft({
      messageId: message.id,
      title: merchant.trim(),
      amount: parsedAmount,
      dateTime: dateTime.trim(),
      source: message.cardLast4
        ? strings.sms.reviewedPreview.sourceValue(message.bank, message.cardLast4)
        : message.bank,
      category: strings.categories[category],
      account: account.label,
    });
    router.push(ROUTES.sms.reviewedPreview);
  };

  const categoryValue = category
    ? categoryConfirmed
      ? strings.categories[category]
      : copy.categoryNeedsConfirmation(strings.categories[category])
    : undefined;

  return (
    <ScreenLayout
      title={review.title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.submit} onPress={submit} />
          <Button title={review.cancel} variant="outline" onPress={goBack} />
        </>
      }
    >
      <Chip label={copy.statusChip} tone="warning" />

      <DividedCard
        title={review.originalTitle(message.bank)}
        subtitle={review.originalSubtitle(formatDateTime(message.receivedAt))}
      >
        <AppText variant="body14" color={colors.text.secondary}>
          {message.body}
        </AppText>
      </DividedCard>

      <FeedbackBanner
        tone="warning"
        title={copy.bannerTitle}
        message={copy.bannerMessage(
          formatCurrency(message.amount),
          source,
          copy.accountsOr(accounts.map((candidate) => candidate.shortLabel)),
        )}
      />

      <SectionHeader title={review.detailsHeading} />
      <Input
        label={copy.amountLabel}
        value={amount}
        onChangeText={setAmount}
        keyboardType="decimal-pad"
        hasError={showError('amount')}
        errorMessage={review.errors.amount}
      />
      <Input
        label={copy.merchantLabel}
        value={merchant}
        onChangeText={setMerchant}
        hasError={showError('merchant')}
        errorMessage={review.errors.required}
      />
      <Input
        label={copy.dateLabel}
        value={dateTime}
        onChangeText={setDateTime}
        hasError={showError('dateTime')}
        errorMessage={review.errors.required}
      />

      <SelectField
        label={copy.categoryLabel}
        value={categoryValue}
        placeholder={copy.categoryPlaceholder}
        onPress={() => togglePicker('category')}
        hasError={showError('category')}
      />
      {openPicker === 'category' ? (
        <OptionList options={CATEGORY_OPTIONS} value={category} onChange={chooseCategory} />
      ) : null}
      {showError('category') ? <FeedbackBanner tone="error" title={review.errors.category} /> : null}

      <SelectField
        label={copy.accountLabel}
        value={account?.label}
        placeholder={copy.accountPlaceholder}
        onPress={() => togglePicker('account')}
        hasError={showError('account')}
      />
      {openPicker === 'account' ? (
        <OptionList
          options={accounts.map((candidate) => ({ value: candidate.id, title: candidate.label }))}
          value={accountId}
          onChange={chooseAccount}
        />
      ) : null}
      {showError('account') ? <FeedbackBanner tone="error" title={review.errors.account} /> : null}

      <OptionCard
        kind="checkbox"
        title={copy.checkDetails}
        selected={detailsChecked}
        onPress={() => setDetailsChecked((value) => !value)}
      />
      <OptionCard
        kind="checkbox"
        title={copy.checkAccount}
        selected={accountChecked}
        onPress={() => setAccountChecked((value) => !value)}
      />
      {showError('checks') ? <FeedbackBanner tone="error" title={copy.checksRequired} /> : null}

      {isMockSource('sms') ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.footnote}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

export default SmsReviewUnmatchedScreen;
