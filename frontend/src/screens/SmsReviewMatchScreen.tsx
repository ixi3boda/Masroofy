import React, { useState } from 'react';
import { Redirect, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import SelectField from '@components/atoms/SelectField';
import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import SectionHeader from '@components/molecules/SectionHeader';
import ScreenLayout from '@components/templates/ScreenLayout';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { smsService } from '@/services/smsService';
import { strings } from '@/strings';
import { formatCurrency, formatDateTime } from '@/utils/formatters';

const review = strings.sms.review;
const copy = review.match;

/**
 * 04-04 · Review Bank SMS: the message duplicates a recorded expense, so confirming only links them.
 * The extracted details are shown read-only: they are the existing record's, and linking doesn't change it.
 */
const SmsReviewMatchScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const message = smsService.getMessage(id);
  const goBack = useGoBack(ROUTES.sms.messages);

  const [pending, setPending] = useState<'confirm' | 'ignore' | null>(null);

  // Imported again after it was linked: show the link instead of reviewing (or ignoring) it twice.
  if (message?.status === 'reviewed') {
    return <Redirect href={{ pathname: ROUTES.sms.matchConfirmed, params: { id: message.id } }} />;
  }
  if (!message?.match) return <Redirect href={ROUTES.sms.messages} />;
  const { match } = message;

  const confirm = async () => {
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
      <SelectField label={copy.amountLabel} value={String(message.amount)} />
      <SelectField label={copy.merchantLabel} value={match.merchant} />
      <SelectField label={copy.dateLabel} value={formatDateTime(message.receivedAt)} />
      <SelectField label={copy.categoryLabel} value={strings.categories[match.category]} />
      <SelectField label={copy.accountLabel} value={match.account.label} />

      <AppText variant="body12" color={colors.text.secondary}>
        {copy.footnote}
      </AppText>
    </ScreenLayout>
  );
};

export default SmsReviewMatchScreen;
