import React from 'react';
import { router } from 'expo-router';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import StateSummary from '@components/molecules/StateSummary';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import SummaryCard from '@components/organisms/SummaryCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { ROUTES } from '@/navigation/routes';
import { strings } from '@/strings';
import { useHardwareBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.passwordUpdated;

// The reset is finished, so every "back" lands on login rather than the reset form.
const returnToLogin = () => router.dismissTo(ROUTES.auth.login);

const PasswordUpdatedScreen: React.FC = () => {
  useHardwareBack(returnToLogin);
  const isMock = isMockSource('auth');

  return (
    <ScreenLayout
      title={copy.title}
      onBack={returnToLogin}
      footer={<Button title={copy.submit} onPress={returnToLogin} />}
    >
      {isMock ? <Chip label={copy.previewChip} tone="info" /> : null}

      <StateSummary icon="shield-check" heading={copy.heading} description={copy.description} />

      <SummaryCard heading={copy.nextHeading} rows={copy.nextSteps} />

      {isMock ? <FeedbackBanner tone="info" title={copy.previewTitle} message={copy.previewMessage} /> : null}
    </ScreenLayout>
  );
};

export default PasswordUpdatedScreen;
