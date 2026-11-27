import React, { useState } from 'react';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import StateSummary from '@components/molecules/StateSummary';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import RequirementList, { Requirement } from '@components/molecules/RequirementList';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { authService } from '@/services/authService';
import { usePasswordResetStore } from '@/store/passwordResetStore';
import { strings } from '@/strings';
import { getErrorMessage, getFieldErrorCodes, getFieldErrors } from '@/utils/errors';
import { getPasswordMatchError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';
import { usePasswordRequirements } from '@/hooks/usePasswordRequirements';

const copy = strings.auth.resetPassword;
type FieldName = 'password' | 'confirmPassword';
const API_FIELDS: Record<string, FieldName> = { newPassword: 'password', confirmPassword: 'confirmPassword' };

const ResetPasswordScreen: React.FC = () => {
  const { resetToken, email, clear: clearResetFlow } = usePasswordResetStore();
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [showMismatch, setShowMismatch] = useState(false);
  const goBack = useGoBack(ROUTES.auth.login);
  // The account's name is not known on this screen, so only the server can confirm NO_PERSONAL_INFO.
  const passwordRules = usePasswordRequirements(password, {
    personal: { email: email ?? undefined },
    personalInfoComplete: false,
  });

  const passwordsMatch = confirmPassword.length > 0 && password === confirmPassword;
  const matchRequirement: Requirement = {
    key: 'PASSWORDS_MATCH',
    label: copy.passwordsMatch,
    status: passwordsMatch ? 'met' : showMismatch ? 'failed' : 'pending',
  };
  const canSubmit = password.length > 0 && confirmPassword.length > 0;

  const setField = (field: FieldName, value: string) => {
    if (field === 'password') setPassword(value);
    if (field === 'confirmPassword') setConfirmPassword(value);
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async () => {
    const errors: Partial<Record<FieldName, string>> = {
      password: passwordRules.isValid ? undefined : strings.validation.passwordRequirementsNotMet,
      confirmPassword: getPasswordMatchError(password, confirmPassword) ?? undefined,
    };
    passwordRules.revealFailures();
    setShowMismatch(true);
    setFieldErrors(errors);
    setFormError(null);
    if (Object.values(errors).some(Boolean)) return;

    setSubmitting(true);
    try {
      await authService.resetPassword({ resetToken: resetToken ?? '', newPassword: password, confirmPassword });
      clearResetFlow();
      router.replace(ROUTES.auth.passwordUpdated);
    } catch (err) {
      const rejectedRules = getFieldErrorCodes(err, 'newPassword');
      passwordRules.setServerFailures(rejectedRules);
      const serverErrors = getFieldErrors(err, API_FIELDS);
      if (rejectedRules.some(passwordRules.isChecklistRule)) {
        serverErrors.password = strings.validation.passwordRequirementsNotMet;
      }
      setFieldErrors(serverErrors);
      // A banner repeating a field's own message adds nothing (e.g. PASSWORD_REUSED, PASSWORDS_DO_NOT_MATCH).
      const message = getErrorMessage(err);
      setFormError(Object.values(serverErrors).includes(message) ? null : message);
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

      {formError ? <FeedbackBanner tone="error" title={copy.errorTitle} message={formError} /> : null}

      <Input
        label={copy.newPasswordLabel}
        placeholder={copy.newPasswordPlaceholder}
        value={password}
        onChangeText={(value) => setField('password', value)}
        hasError={!!fieldErrors.password}
        errorMessage={fieldErrors.password}
        secureTextEntry
      />
      <RequirementList items={passwordRules.requirements} />
      <Input
        label={copy.confirmLabel}
        placeholder={copy.confirmPlaceholder}
        value={confirmPassword}
        onChangeText={(value) => setField('confirmPassword', value)}
        hasError={!!fieldErrors.confirmPassword}
        errorMessage={fieldErrors.confirmPassword}
        secureTextEntry
      />
      <RequirementList items={[matchRequirement]} />

      {isMockSource('auth') ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.previewNotice}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

export default ResetPasswordScreen;
