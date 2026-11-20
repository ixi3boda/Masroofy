import React, { useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import StateSummary from '@components/molecules/StateSummary';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import SummaryCard from '@components/organisms/SummaryCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { PASSWORD_MIN_LENGTH } from '@/constants/app';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { strings } from '@/strings';
import { getNewPasswordError, getPasswordMatchError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.resetPassword;

const ResetPasswordScreen: React.FC = () => {
  const { email = '' } = useLocalSearchParams<{ email?: string }>();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const goBack = useGoBack(ROUTES.auth.login);

  const canSubmit = password.length >= PASSWORD_MIN_LENGTH && password === confirmPassword;

  const handleSubmit = async () => {
    const validationError = getNewPasswordError(password) ?? getPasswordMatchError(password, confirmPassword);
    if (validationError) {
      setError(validationError);
      return;
    }
    setError(null);
    setSubmitting(true);
    try {
      await authService.resetPassword(email, password);
      router.replace(ROUTES.auth.passwordUpdated);
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
          <Button title={copy.submit} onPress={handleSubmit} loading={submitting} disabled={!canSubmit} />
          <Button
            title={strings.common.backToLogin}
            variant="outline"
            onPress={() => router.dismissTo(ROUTES.auth.login)}
          />
        </>
      }
    >
      <StateSummary icon="lock-keyhole" heading={copy.heading} description={copy.description} />

      <Input
        label={copy.newPasswordLabel}
        placeholder={copy.newPasswordPlaceholder}
        value={password}
        onChangeText={(value) => {
          setPassword(value);
          setError(null);
        }}
        secureTextEntry
      />
      <Input
        label={copy.confirmLabel}
        placeholder={copy.confirmPlaceholder}
        value={confirmPassword}
        onChangeText={(value) => {
          setConfirmPassword(value);
          setError(null);
        }}
        secureTextEntry
      />

      {error ? <FeedbackBanner tone="error" title={copy.errorTitle} message={error} /> : null}

      <SummaryCard heading={copy.requirementsHeading} rows={copy.requirements} />

      <AppText variant="body12" color={colors.text.secondary}>
        {copy.previewNotice}
      </AppText>
    </ScreenLayout>
  );
};

export default ResetPasswordScreen;
