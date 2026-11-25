import React from 'react';
import { Redirect } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ListRow from '@components/molecules/ListRow';
import StateSummary from '@components/molecules/StateSummary';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { smsService } from '@/services/smsService';
import { useSmsReviewStore } from '@/store/smsReviewStore';
import { strings } from '@/strings';
import { formatCurrency, formatMonthName } from '@/utils/formatters';

const copy = strings.sms.reviewedPreview;

const backToMessages = () => router.dismissTo(ROUTES.sms.messages);

/**
 * 04-08 · SMS Confirmation: what the user verified on an unmatched or withdrawal
 * review. As in the design, nothing is saved and the message stays "New".
 */
const SmsReviewedPreviewScreen: React.FC = () => {
  const draft = useSmsReviewStore((state) => state.draft);
  const message = draft ? smsService.getMessage(draft.messageId) : undefined;
  const goBack = useGoBack(ROUTES.sms.messages);

  if (!draft || !message) return <Redirect href={ROUTES.sms.messages} />;

  const isMock = isMockSource('sms');

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.backToMessages} onPress={backToMessages} />
          <Button title={copy.reviewDetails} variant="outline" onPress={goBack} />
        </>
      }
    >
      {isMock ? <Chip label={copy.previewChip} tone="warning" /> : null}

      <StateSummary icon="check" heading={copy.heading} description={copy.description} />

      <DividedCard>
        <ListRow title={draft.title} subtitle={copy.dateTime(draft.dateTime)} trailing={formatCurrency(draft.amount)} />
        <ListRow title={copy.source} trailing={draft.source} />
        <ListRow title={copy.category} trailing={draft.category} />
        <ListRow title={copy.account} trailing={draft.account} status={{ label: copy.notSavedChip, tone: 'info' }} />
      </DividedCard>

      <FeedbackBanner title={copy.bannerTitle} message={copy.bannerMessage} />

      {isMock ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.footnote(formatMonthName(message.receivedAt))}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

export default SmsReviewedPreviewScreen;
