import React from 'react';
import { router } from 'expo-router';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import StateSummary from '@components/molecules/StateSummary';
import SummaryCard from '@components/organisms/SummaryCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ScreenLayout from '@components/templates/ScreenLayout';
import { useHardwareBack } from '@/hooks/useBackNavigation';

// The reset is finished, so every "back" lands on login rather than the reset form.
const returnToLogin = () => router.dismissTo('/(auth)/login');

const PasswordUpdatedScreen: React.FC = () => {
  useHardwareBack(returnToLogin);

  return (
    <ScreenLayout
      title="Password updated"
      onBack={returnToLogin}
      footer={<Button title="Continue to Login" onPress={returnToLogin} />}
    >
      <Chip label="Confirmation preview" tone="info" />

      <StateSummary
        icon="shield-check"
        heading="Password updated"
        description="Your password has been reset successfully."
      />

      <SummaryCard heading="Ready to return" rows={['Use your new password the next time you log in.']} />

      <FeedbackBanner
        tone="info"
        title="Static confirmation"
        message="No password has been changed. This preview does not authenticate an account."
      />
    </ScreenLayout>
  );
};

export default PasswordUpdatedScreen;
