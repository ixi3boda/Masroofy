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
import SectionHeader from '@components/molecules/SectionHeader';
import ScreenLayout from '@components/templates/ScreenLayout';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { smsService } from '@/services/smsService';
import { strings } from '@/strings';
import { formatCurrency, formatDateTime } from '@/utils/formatters';
import { parseAmount } from '@/utils/validators';

const review = strings.sms.review;
const copy = review.match;

/** 04-04 · Review Bank SMS: the message duplicates a recorded expense, so confirming only links them. */
const SmsReviewMatchScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const message = smsService.getMessage(id);
  const goBack = useGoBack(ROUTES.sms.messages);

  const [amount, setAmount] = useState(() => (message ? String(message.amount) : ''));
  const [merchant, setMerchant] = useState(message?.match?.merchant ?? '');
  const [dateTime, setDateTime] = useState(() => (message ? formatDateTime(message.receivedAt) : ''));
  const [submitted, setSubmitted] = useState(false);
  const [pending, setPending] = useState<'confirm' | 'ignore' | null>(null);

  if (!message?.match) return <Redirect href={ROUTES.sms.messages} />;
  const { match } = message;

  const amountInvalid = submitted && parseAmount(amount) === null;
  const merchantMissing = submitted && !merchant.trim();
  const dateMissing = submitted && !dateTime.trim();

  const confirm = async () => {
    setSubmitted(true);
    if (parseAmount(amount) === null || !merchant.trim() || !dateTime.trim()) return;
    setPending('confirm');
    try {
      await smsService.confirmMatch(message.id);
      router.replace({ pathname: ROUTES.sms.matchConfirmed, params: { id: message.id } });
    } finally {
      setPending(null);
    }
  };

  const ignore = async () => {
    setPending('ignore');
    try {
      await smsService.ignoreMessage(message.id);
      router.dismissTo(ROUTES.sms.messages);
    } finally {
      setPending(null);
    }
  };

  return (
    <ScreenLayout
      title={review.title}
      onBack={goBack}
      footer={
        <>
          <Button
            title={copy.confirm}
            loading={pending === 'confirm'}
            disabled={pending !== null}
            onPress={confirm}
          />
          <Button
            title={copy.ignore}
            variant="outline"
            loading={pending === 'ignore'}
            disabled={pending !== null}
            onPress={ignore}
          />
        </>
      }
    >
      <DividedCard
        title={review.originalTitle(message.bank)}
        subtitle={review.originalSubtitle(formatDateTime(message.receivedAt))}
      >
        <AppText variant="body14">{message.body}</AppText>
      </DividedCard>

      <Chip label={copy.confidenceChip} tone="info" />

      <FeedbackBanner
        tone="warning"
        icon="copy-check"
        title={copy.bannerTitle(match.merchant, formatCurrency(message.amount))}
        message={copy.bannerMessage}
      />

      <SectionHeader title={review.detailsHeading} />
      <Input
        label={copy.amountLabel}
        value={amount}
        onChangeText={setAmount}
        keyboardType="decimal-pad"
        hasError={amountInvalid}
        errorMessage={review.errors.amount}
      />
      <Input
        label={copy.merchantLabel}
        value={merchant}
        onChangeText={setMerchant}
        hasError={merchantMissing}
        errorMessage={review.errors.required}
      />
      <Input
        label={copy.dateLabel}
        value={dateTime}
        onChangeText={setDateTime}
        hasError={dateMissing}
        errorMessage={review.errors.required}
      />
      <SelectField label={copy.categoryLabel} value={strings.categories[match.category]} />
      <SelectField label={copy.accountLabel} value={match.account.label} />

      <AppText variant="body12" color={colors.text.secondary}>
        {copy.footnote}
      </AppText>
    </ScreenLayout>
  );
};

export default SmsReviewMatchScreen;
