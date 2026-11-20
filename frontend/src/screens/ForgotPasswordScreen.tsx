import React, { useState } from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import Card from '@components/atoms/Card';
import Icon from '@components/atoms/Icon';
import StateSummary from '@components/molecules/StateSummary';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import AuthScreenLayout from '@components/templates/AuthScreenLayout';
import { mockAuthService } from '@/services/mockAuthService';
import { getEmailError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';

const ForgotPasswordScreen: React.FC = () => {
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const goBack = useGoBack('/(auth)/login');

  const handleSubmit = async () => {
    const error = getEmailError(email);
    if (error) {
      setEmailError(error);
      return;
    }
    setEmailError(null);
    setSubmitting(true);
    try {
      const { email: requestedEmail } = await mockAuthService.requestPasswordReset(email);
      router.push({ pathname: '/(auth)/check-email', params: { email: requestedEmail } });
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthScreenLayout
      title="Forgot password"
      onBack={goBack}
      footer={
        <>
          <Button title="Request reset link" onPress={handleSubmit} loading={submitting} disabled={!email} />
          <Button title="Back to log in" variant="outline" onPress={() => router.dismissTo('/(auth)/login')} />
        </>
      }
    >
      <StateSummary
        icon={<Icon name="mail" size={42} color={colors.text.inverse} />}
        heading="Let’s reset your password"
        description="Enter the email associated with your account to request a password reset link."
      />

      <Card>
        <Input
          label="Email address"
          placeholder="Enter your email"
          value={email}
          onChangeText={(value) => {
            setEmail(value);
            setEmailError(null);
          }}
          hasError={!!emailError}
          errorMessage={emailError}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        {!emailError ? (
          <AppText variant="body12" color={colors.text.secondary}>
            Check the address before continuing.
          </AppText>
        ) : null}
      </Card>

      <FeedbackBanner tone="info" title="Email request preview" message="This is a static request screen. No email will be sent." />
    </AuthScreenLayout>
  );
};

export default ForgotPasswordScreen;
