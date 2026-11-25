import React, { useState } from 'react';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import StateSummary from '@components/molecules/StateSummary';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import SummaryCard from '@components/organisms/SummaryCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { PASSWORD_MIN_LENGTH } from '@/constants/app';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { authService } from '@/services/authService';
import { usePasswordResetStore } from '@/store/passwordResetStore';
import { strings } from '@/strings';
import { getErrorMessage, getFieldErrors } from '@/utils/errors';
import { getNewPasswordError, getPasswordMatchError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.resetPassword;
// Both backend fields are shown in this screen's single error banner.
const API_FIELDS: Record<string, 'password'> = { newPassword: 'password', confirmPassword: 'password' };

const ResetPasswordScreen: React.FC = () => {
  const { resetToken, clear: clearResetFlow } = usePasswordResetStore();
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
      await authService.resetPassword({ resetToken: resetToken ?? '', newPassword: password, confirmPassword });
      clearResetFlow();
      router.replace(ROUTES.auth.passwordUpdated);
    } catch (err) {
      setError(getFieldErrors(err, API_FIELDS).password ?? getErrorMessage(err));
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

      {isMockSource('auth') ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.previewNotice}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

export default ResetPasswordScreen;
