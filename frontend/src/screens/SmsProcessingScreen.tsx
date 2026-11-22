import React, { useEffect } from 'react';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
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
import { smsService } from '@/services/smsService';
import { strings } from '@/strings';
import { BankMessageReview } from '@/types/sms';

const copy = strings.sms.processing;

const REVIEW_ROUTES = {
  match: ROUTES.sms.reviewMatch,
  unmatched: ROUTES.sms.reviewUnmatched,
  withdrawal: ROUTES.sms.classifyWithdrawal,
} as const satisfies Record<BankMessageReview, string>;

/**
 * 04-03 · Reviewing Message: extracts the details, then replaces itself with the review that
 * fits the message. It always sits right above Bank Messages, so back = Cancel review.
 */
const SmsProcessingScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const message = smsService.getMessage(id);
  const messageId = message?.id;
  const cancelReview = useGoBack(ROUTES.sms.messages);

  useEffect(() => {
    if (!messageId) return undefined;
    let active = true;
    smsService
      .extractDetails(messageId)
      .then((review) => {
        if (active) router.replace({ pathname: REVIEW_ROUTES[review], params: { id: messageId } });
      })
      .catch(() => {
        if (active) router.replace(ROUTES.sms.importFailed);
      });
    // Leaving the screen (Cancel review / back) stops the hand-off to the review screen.
    return () => {
      active = false;
    };
  }, [messageId]);

  if (!message) return <Redirect href={ROUTES.sms.messages} />;

  const isMock = isMockSource('sms');

  return (
    <ScreenLayout
      title={copy.title}
      onBack={cancelReview}
      footer={<Button title={copy.cancel} variant="outline" onPress={cancelReview} />}
    >
      {isMock ? <Chip label={copy.previewChip} tone="info" /> : null}

      <StateSummary icon="scan-text" heading={copy.heading} description={copy.description} />

      <DividedCard>
        <ListRow title={copy.source} trailing={message.bank} body={message.body} />
        {copy.steps.map((step) => (
          <ListRow key={step.label} title={step.label} trailing={step.status} />
        ))}
      </DividedCard>

      {isMock ? <FeedbackBanner title={copy.bannerTitle} message={copy.bannerMessage} /> : null}
    </ScreenLayout>
  );
};

export default SmsProcessingScreen;
