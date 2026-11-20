import React from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import Icon from '@components/atoms/Icon';
import StateSummary from '@components/molecules/StateSummary';
import SummaryCard from '@components/molecules/SummaryCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import AuthScreenLayout from '@components/templates/AuthScreenLayout';
import { useHardwareBack } from '@/hooks/useBackNavigation';

// The reset is finished, so every "back" lands on login rather than the reset form.
const returnToLogin = () => router.dismissTo('/(auth)/login');

const PasswordUpdatedScreen: React.FC = () => {
  useHardwareBack(returnToLogin);

  return (
    <AuthScreenLayout
      title="Password updated"
      onBack={returnToLogin}
      footer={<Button title="Continue to Login" onPress={returnToLogin} />}
    >
      <Chip label="Confirmation preview" tone="info" />

      <StateSummary
        icon={<Icon name="shield-check" size={42} color={colors.text.inverse} />}
        heading="Password updated"
        description="Your password has been reset successfully."
      />

      <SummaryCard heading="Ready to return" rows={['Use your new password the next time you log in.']} />

      <FeedbackBanner
        tone="info"
        title="Static confirmation"
        message="No password has been changed. This preview does not authenticate an account."
      />
    </AuthScreenLayout>
  );
};

export default PasswordUpdatedScreen;
