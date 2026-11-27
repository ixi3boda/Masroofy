import React from 'react';
import { Redirect, router, useLocalSearchParams } from 'expo-router';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import StateSummary from '@components/molecules/StateSummary';
import TransactionRecordCard from '@components/organisms/TransactionRecordCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { CATEGORY_ICONS } from '@/constants/categories';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { dashboardService } from '@/services/dashboardService';
import { smsService } from '@/services/smsService';
import { strings } from '@/strings';
import { formatCurrency, formatDate, formatMonthName } from '@/utils/formatters';

const copy = strings.sms.matchConfirmed;

const viewReviewedMessages = () =>
  router.dismissTo({ pathname: ROUTES.sms.messages, params: { tab: 'reviewed' } });
const goHome = () => router.dismissTo(ROUTES.app.home);

/** 04-05 · SMS Confirmed: the message is linked to the existing record; spending is unchanged. */
const SmsMatchConfirmedScreen: React.FC = () => {
  const { id } = useLocalSearchParams<{ id: string }>();
  const message = smsService.getMessage(id);
  const goBack = useGoBack(ROUTES.sms.messages);

  if (!message?.match) return <Redirect href={ROUTES.sms.messages} />;

  const { match } = message;
  const category = strings.categories[match.category];
  const month = formatMonthName(message.receivedAt);
  const spending = formatCurrency(dashboardService.getSummary().totalExpense);
  const amount = formatCurrency(message.amount);

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.viewDetails} onPress={viewReviewedMessages} />
          <Button title={copy.backHome} variant="outline" onPress={goHome} />
        </>
      }
    >
      <StateSummary icon="link" heading={copy.heading} description={copy.description(message.bank, match.merchant)} />

      <Chip label={copy.chip} tone="success" />

      <TransactionRecordCard
        transaction={{
          title: match.merchant,
          meta: copy.recordMeta(category, formatDate(message.receivedAt)),
          amount,
          icon: CATEGORY_ICONS[match.category],
        }}
        details={[
          { label: copy.account, value: match.account.shortLabel },
          { label: copy.status, value: copy.recorded },
        ]}
        footnote={copy.footnote(month, spending)}
      />

      <FeedbackBanner tone="success" title={copy.bannerTitle(month, spending)} message={copy.bannerMessage(amount)} />
    </ScreenLayout>
  );
};

export default SmsMatchConfirmedScreen;
