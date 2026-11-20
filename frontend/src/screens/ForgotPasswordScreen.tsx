import React, { useState } from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import Card from '@components/atoms/Card';
import StateSummary from '@components/molecules/StateSummary';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { strings } from '@/strings';
import { getErrorMessage, isApiError } from '@/utils/errors';
import { getEmailError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.forgotPassword;
const { fields } = strings.common;

const ForgotPasswordScreen: React.FC = () => {
  const [email, setEmail] = useState('');
  const [emailError, setEmailError] = useState<string | undefined>();
  const [submitting, setSubmitting] = useState(false);
  const goBack = useGoBack(ROUTES.auth.login);

  const handleSubmit = async () => {
    const error = getEmailError(email);
    if (error) {
      setEmailError(error);
      return;
    }
    setEmailError(undefined);
    setSubmitting(true);
    try {
      const { email: requestedEmail, verification } = await authService.requestPasswordReset(email);
      router.push({
        pathname: ROUTES.auth.checkEmail,
        params: { email: requestedEmail, resendIn: String(verification.resendAvailableInSeconds) },
      });
    } catch (error) {
      // A code was sent less than a minute ago: go on to the code screen with the remaining wait.
      if (isApiError(error, 'RESEND_COOLDOWN')) {
        router.push({
          pathname: ROUTES.auth.checkEmail,
          params: { email: email.trim().toLowerCase(), resendIn: String(error.details.retryAfterSeconds ?? '') },
        });
        return;
      }
      setEmailError(getErrorMessage(error));
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.submit} onPress={handleSubmit} loading={submitting} disabled={!email} />
          <Button
            title={strings.common.backToLogin}
            variant="outline"
            onPress={() => router.dismissTo(ROUTES.auth.login)}
          />
        </>
      }
    >
      <StateSummary icon="mail" heading={copy.heading} description={copy.description} />

      <Card>
        <Input
          label={fields.emailLabel}
          placeholder={fields.emailPlaceholder}
          value={email}
          onChangeText={(value) => {
            setEmail(value);
            setEmailError(undefined);
          }}
          hasError={!!emailError}
          errorMessage={emailError}
          keyboardType="email-address"
          autoCapitalize="none"
        />
        {!emailError ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {copy.emailHint}
          </AppText>
        ) : null}
      </Card>

      {isMockSource('auth') ? (
        <FeedbackBanner tone="info" title={copy.previewTitle} message={copy.previewMessage} />
      ) : null}
    </ScreenLayout>
  );
};

export default ForgotPasswordScreen;
