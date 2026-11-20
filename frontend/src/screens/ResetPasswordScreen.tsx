import React, { useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import StateSummary from '@components/molecules/StateSummary';
import SummaryCard from '@components/organisms/SummaryCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ScreenLayout from '@components/templates/ScreenLayout';
import { mockAuthService } from '@/services/mockAuthService';
import { getNewPasswordError, getPasswordMatchError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';

const REQUIREMENTS = [
  '○ At least 8 characters',
  '○ Include at least one number',
  '○ Include at least one capital letter',
  '○ Both passwords must match',
];

const ResetPasswordScreen: React.FC = () => {
  const { email = '' } = useLocalSearchParams<{ email?: string }>();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const goBack = useGoBack('/(auth)/login');

  const canSubmit = password.length >= 8 && password === confirmPassword;

  const handleSubmit = async () => {
    const validationError = getNewPasswordError(password) ?? getPasswordMatchError(password, confirmPassword);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await mockAuthService.resetPassword(email, password);
      router.replace('/(auth)/password-updated');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScreenLayout
      title="Set new password"
      onBack={goBack}
      footer={
        <>
          <Button title="Update password" onPress={handleSubmit} loading={submitting} disabled={!canSubmit} />
          <Button title="Back to log in" variant="outline" onPress={() => router.dismissTo('/(auth)/login')} />
        </>
      }
    >
      <StateSummary
        icon="lock-keyhole"
        heading="Choose a new password"
        description="Use a password you have not used for this account before."
      />

      <Input
        label="New password"
        placeholder="Enter a new password"
        value={password}
        onChangeText={(value) => {
          setPassword(value);
          setError(null);
        }}
        secureTextEntry
      />
      <Input
        label="Confirm new password"
        placeholder="Re-enter your new password"
        value={confirmPassword}
        onChangeText={(value) => {
          setConfirmPassword(value);
          setError(null);
        }}
        secureTextEntry
      />

      {error ? <FeedbackBanner tone="error" title="Could not update password" message={error} /> : null}

      <SummaryCard heading="Password requirements" rows={REQUIREMENTS} />

      <AppText variant="body12" color={colors.text.secondary}>
        Static design preview only. No account, sign-in or email action is performed.
      </AppText>
    </ScreenLayout>
  );
};

export default ResetPasswordScreen;
