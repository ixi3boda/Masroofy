import React, { useState } from 'react';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import BrandMark from '@components/molecules/BrandMark';
import OptionCard from '@components/molecules/OptionCard';
import RequirementList from '@components/molecules/RequirementList';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { authService } from '@/services/authService';
import { ROUTES } from '@/navigation/routes';
import { router } from '@/navigation/router';
import { strings } from '@/strings';
import { getErrorMessage, getFieldErrorCodes, getFieldErrors } from '@/utils/errors';
import { getEmailError, getRequiredError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';
import { usePasswordRequirements } from '@/hooks/usePasswordRequirements';

type FieldName = 'fullName' | 'email' | 'password';

const copy = strings.auth.signUp;
const { fields } = strings.common;
const API_FIELDS: Record<string, FieldName> = { fullName: 'fullName', email: 'email', password: 'password' };

const SignUpScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.auth.welcome);
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const passwordRules = usePasswordRequirements(password, {
    personal: { fullName, email },
    personalInfoComplete: fullName.trim().length > 0 && email.trim().length > 0,
  });

  const canSubmit = fullName.trim().length > 0 && email.trim().length > 0 && password.length > 0 && agreed;

  const setField = (field: FieldName, value: string) => {
    if (field === 'fullName') setFullName(value);
    if (field === 'email') setEmail(value);
    if (field === 'password') setPassword(value);
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async () => {
    const errors: Partial<Record<FieldName, string>> = {
      fullName: getRequiredError(fullName, strings.validation.fieldNames.fullName) ?? undefined,
      email: getEmailError(email) ?? undefined,
      password: passwordRules.isValid ? undefined : strings.validation.passwordRequirementsNotMet,
    };
    passwordRules.revealFailures();
    setFieldErrors(errors);
    setFormError(null);
    if (Object.values(errors).some(Boolean) || !agreed) return;

    setSubmitting(true);
    try {
      const { email: confirmedEmail, verification } = await authService.signUp({
        fullName,
        email,
        password,
        acceptedTerms: agreed,
      });
      router.push({
        pathname: ROUTES.auth.verifyEmail,
        params: { email: confirmedEmail, resendIn: String(verification.resendAvailableInSeconds) },
      });
    } catch (error) {
      const rejectedRules = getFieldErrorCodes(error, 'password');
      passwordRules.setServerFailures(rejectedRules);
      const serverErrors = getFieldErrors(error, API_FIELDS);
      if (rejectedRules.some(passwordRules.isChecklistRule)) {
        serverErrors.password = strings.validation.passwordRequirementsNotMet;
      }
      setFieldErrors(serverErrors);
      // A banner repeating a field's own message adds nothing.
      const message = getErrorMessage(error);
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
            title={copy.haveAccount}
            variant="outline"
            onPress={() => router.dismissTo(ROUTES.auth.login)}
          />
        </>
      }
    >
      <BrandMark />
      <AppText variant="subheading16">{copy.heading}</AppText>

      {formError ? <FeedbackBanner tone="error" title={copy.errorTitle} message={formError} /> : null}

      <Input
        label={copy.fullNameLabel}
        placeholder={copy.fullNamePlaceholder}
        value={fullName}
        onChangeText={(value) => setField('fullName', value)}
        hasError={!!fieldErrors.fullName}
        errorMessage={fieldErrors.fullName}
        autoCapitalize="words"
      />
      <Input
        label={fields.emailLabel}
        placeholder={fields.emailPlaceholder}
        value={email}
        onChangeText={(value) => setField('email', value)}
        hasError={!!fieldErrors.email}
        errorMessage={fieldErrors.email}
        keyboardType="email-address"
        autoCapitalize="none"
      />
      <Input
        label={fields.passwordLabel}
        placeholder={copy.passwordPlaceholder}
        value={password}
        onChangeText={(value) => setField('password', value)}
        hasError={!!fieldErrors.password}
        errorMessage={fieldErrors.password}
        secureTextEntry
      />
      <RequirementList items={passwordRules.requirements} />

      <OptionCard
        kind="checkbox"
        title={copy.consentTitle}
        description={copy.consentDescription}
        selected={agreed}
        onPress={() => setAgreed((value) => !value)}
      />

      {isMockSource('auth') ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.previewNotice}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

export default SignUpScreen;
