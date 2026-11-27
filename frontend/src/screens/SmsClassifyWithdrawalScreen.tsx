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
import OptionList, { OptionListItem } from '@components/organisms/OptionList';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { smsService } from '@/services/smsService';
import { useSmsReviewStore } from '@/store/smsReviewStore';
import { strings } from '@/strings';
import { formatDateTime } from '@/utils/formatters';
import { parseAmount } from '@/utils/validators';

const review = strings.sms.review;
const copy = review.withdrawal;

type Classification = keyof typeof copy.options;
type Picker = 'source' | 'destination';

const CLASSIFICATIONS: OptionListItem<Classification>[] = (Object.keys(copy.options) as Classification[]).map(
  (value) => ({ value, ...copy.options[value] }),
);

const leaveUnrecorded = () => router.dismissTo(ROUTES.sms.messages);

/** 04-07 · Classify Withdrawal: a withdrawal moves money, so it is classified before anything is recorded. */
const SmsClassifyWithdrawalScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const message = smsService.getMessage(id);
  const goBack = useGoBack(ROUTES.sms.messages);
  const setDraft = useSmsReviewStore((state) => state.setDraft);
  const accounts = smsService.getTrackingAccounts();
  const accountOptions = accounts.map((account) => ({ value: account.id, title: account.label }));

  const [classification, setClassification] = useState<Classification | null>(null);
  const [amount, setAmount] = useState(() => (message ? String(message.amount) : ''));
  const [sourceId, setSourceId] = useState<string | null>(null);
  const [destinationId, setDestinationId] = useState<string | null>(null);
  const [openPicker, setOpenPicker] = useState<Picker | null>(null);
  const [submitted, setSubmitted] = useState(false);

  if (!message) return <Redirect href={ROUTES.sms.messages} />;

  const source = accounts.find((account) => account.id === sourceId);
  const destination = accounts.find((account) => account.id === destinationId);
  const parsedAmount = parseAmount(amount);

  const togglePicker = (picker: Picker) => setOpenPicker((current) => (current === picker ? null : picker));

  const chooseSource = (value: string) => {
    setSourceId(value);
    setOpenPicker(null);
  };

  const chooseDestination = (value: string) => {
    setDestinationId(value);
    setOpenPicker(null);
  };

  const submit = () => {
    setSubmitted(true);
    if (!classification) return;
    if (classification === 'needsClarification') {
      leaveUnrecorded();
      return;
    }
    if (parsedAmount === null || !source || !destination) return;
    setDraft({
      messageId: message.id,
      title: message.bank,
      amount: parsedAmount,
      dateTime: formatDateTime(message.receivedAt),
      source: message.cardLast4
        ? strings.sms.reviewedPreview.sourceValue(message.bank, message.cardLast4)
        : message.bank,
      category: copy.options[classification].title,
      account: copy.transferAccounts(source.label, destination.label),
    });
    router.push(ROUTES.sms.reviewedPreview);
  };

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.submit} onPress={submit} />
          <Button title={copy.leave} variant="outline" onPress={leaveUnrecorded} />
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

      <FeedbackBanner tone="warning" title={copy.bannerTitle} message={copy.bannerMessage} />

      <OptionList options={CLASSIFICATIONS} value={classification} onChange={setClassification} />
      {submitted && !classification ? <FeedbackBanner tone="error" title={copy.classificationRequired} /> : null}

      <Input
        label={copy.amountLabel}
        value={amount}
        onChangeText={setAmount}
        keyboardType="decimal-pad"
        hasError={submitted && parsedAmount === null}
        errorMessage={review.errors.amount}
      />

      <SelectField
        label={copy.sourceLabel}
        value={source?.label}
        placeholder={copy.sourcePlaceholder(message.cardLast4 ? review.cardSource(message.cardLast4) : message.bank)}
        onPress={() => togglePicker('source')}
        hasError={submitted && !source}
      />
      {openPicker === 'source' ? <OptionList options={accountOptions} value={sourceId} onChange={chooseSource} /> : null}

      <SelectField
        label={copy.destinationLabel}
        value={destination?.label}
        placeholder={copy.destinationPlaceholder}
        onPress={() => togglePicker('destination')}
        hasError={submitted && !destination}
      />
      {openPicker === 'destination' ? (
        <OptionList options={accountOptions} value={destinationId} onChange={chooseDestination} />
      ) : null}
      {submitted && (!source || !destination) ? <FeedbackBanner tone="error" title={review.errors.account} /> : null}

      {isMockSource('sms') && !classification ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.footnote(message.bank)}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

export default SmsClassifyWithdrawalScreen;
