import React, { useState } from 'react';
import { TouchableOpacity } from 'react-native';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import BrandMark from '@components/molecules/BrandMark';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import AuthScreenLayout from '@components/templates/AuthScreenLayout';
import { mockAuthService, MockAuthError, MOCK_TEST_ACCOUNTS } from '@/services/mockAuthService';
import { getEmailError, getRequiredError } from '@/utils/validators';

type FieldName = 'email' | 'password';

const LoginScreen: React.FC = () => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const setField = (field: FieldName, value: string) => {
    if (field === 'email') setEmail(value);
    if (field === 'password') setPassword(value);
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async () => {
    const errors: Partial<Record<FieldName, string>> = {
      email: getEmailError(email) ?? undefined,
      password: getRequiredError(password, 'password') ?? undefined,
    };
    setFieldErrors(errors);
    setFormError(null);
    if (Object.values(errors).some(Boolean)) return;

    setSubmitting(true);
    try {
      await mockAuthService.logIn(email, password);
      router.replace('/(app)/home');
    } catch (error) {
      setFormError(error instanceof MockAuthError ? error.message : 'Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthScreenLayout
      title="Log in"
      onBack={() => router.back()}
      footer={
        <>
          <Button
            title="Log in"
            onPress={handleSubmit}
            loading={submitting}
            disabled={!email || !password}
          />
          <Button
            title="Create an account"
            variant="outline"
            onPress={() => router.push('/(auth)/sign-up')}
          />
        </>
      }
    >
      <BrandMark />
      <AppText variant="subheading16">Welcome back</AppText>
      <AppText variant="body14" color={colors.text.secondary}>
        Log in to your Masroofy account.
      </AppText>

      {formError ? <FeedbackBanner tone="error" title="Could not log in" message={formError} /> : null}

      <Input
        label="Email address"
        placeholder="Enter your email"
        value={email}
        onChangeText={(value) => setField('email', value)}
        hasError={!!fieldErrors.email}
        errorMessage={fieldErrors.email}
        keyboardType="email-address"
        autoCapitalize="none"
      />
      <Input
        label="Password"
        placeholder="Enter your password"
        value={password}
        onChangeText={(value) => setField('password', value)}
        hasError={!!fieldErrors.password}
        errorMessage={fieldErrors.password}
        secureTextEntry
      />

      <TouchableOpacity onPress={() => router.push('/(auth)/forgot-password')}>
        <AppText variant="subheading14" color={colors.primary}>
          Forgot password?
        </AppText>
      </TouchableOpacity>

      <AppText variant="body12" color={colors.text.secondary}>
        Static design preview only. Use {MOCK_TEST_ACCOUNTS[0].email} / {MOCK_TEST_ACCOUNTS[0].password} in
        this preview.
      </AppText>
    </AuthScreenLayout>
  );
};

export default LoginScreen;
