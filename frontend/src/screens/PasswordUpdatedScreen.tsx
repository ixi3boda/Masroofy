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

const PasswordUpdatedScreen: React.FC = () => {
  return (
    <AuthScreenLayout
      title="Password updated"
      onBack={() => router.back()}
      footer={<Button title="Continue to Login" onPress={() => router.replace('/(auth)/login')} />}
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
