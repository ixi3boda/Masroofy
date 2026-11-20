import React, { useState } from 'react';
import { StyleSheet } from 'react-native';
import { router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import BrandMark from '@components/molecules/BrandMark';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { MOCK_TEST_ACCOUNTS } from '@/mocks';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { useSessionStore } from '@/store/sessionStore';
import { strings } from '@/strings';
import { getErrorMessage, getFieldErrors, isApiError } from '@/utils/errors';
import { getEmailError, getRequiredError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';

type FieldName = 'email' | 'password';

const copy = strings.auth.login;
const { fields } = strings.common;
const demoAccount = MOCK_TEST_ACCOUNTS[0];
const API_FIELDS: Record<string, FieldName> = { email: 'email', password: 'password' };

/** Param: `email`, to pre-fill the field (e.g. after verifying the email). */
const LoginScreen: React.FC = () => {
  const { email: initialEmail = '' } = useLocalSearchParams<{ email?: string }>();
  const [email, setEmail] = useState(initialEmail);
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const signIn = useSessionStore((state) => state.signIn);
  const goBack = useGoBack(ROUTES.auth.welcome);

  const setField = (field: FieldName, value: string) => {
    if (field === 'email') setEmail(value);
    if (field === 'password') setPassword(value);
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async () => {
    const errors: Partial<Record<FieldName, string>> = {
      email: getEmailError(email) ?? undefined,
      password: getRequiredError(password, strings.validation.fieldNames.password) ?? undefined,
    };
    setFieldErrors(errors);
    setFormError(null);
    if (Object.values(errors).some(Boolean)) return;

    setSubmitting(true);
    try {
      signIn(await authService.logIn(email, password));
      router.replace(ROUTES.app.home);
    } catch (error) {
      // Right password, unverified email: verify first (login sends no code; that screen asks for one).
      if (isApiError(error, 'EMAIL_NOT_VERIFIED')) {
        router.push({ pathname: ROUTES.auth.verifyEmail, params: { email: email.trim().toLowerCase(), resend: '1' } });
        return;
      }
      setFieldErrors(getFieldErrors(error, API_FIELDS));
      setFormError(getErrorMessage(error));
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
          <Button title={copy.submit} onPress={handleSubmit} loading={submitting} disabled={!email || !password} />
          <Button
            title={copy.createAccount}
            variant="outline"
            onPress={() => router.dismissTo(ROUTES.auth.signUp)}
          />
        </>
      }
    >
      <BrandMark />
      <AppText variant="subheading16">{copy.heading}</AppText>
      <AppText variant="body14" color={colors.text.secondary}>
        {copy.intro}
      </AppText>

      {formError ? <FeedbackBanner tone="error" title={copy.errorTitle} message={formError} /> : null}

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

      <Button
        title={copy.forgotPassword}
        variant="link"
        size="sm"
        onPress={() => router.push(ROUTES.auth.forgotPassword)}
        style={styles.forgotPassword}
      />

      {isMockSource('auth') ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.previewNotice(demoAccount.email, demoAccount.password)}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

const styles = StyleSheet.create({
  forgotPassword: { paddingHorizontal: 0 },
});

export default LoginScreen;
