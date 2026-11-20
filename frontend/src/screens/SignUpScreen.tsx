import React, { useState } from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import BrandMark from '@components/molecules/BrandMark';
import ConsentCheckboxCard from '@components/molecules/ConsentCheckboxCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import AuthScreenLayout from '@components/templates/AuthScreenLayout';
import { mockAuthService, MockAuthError } from '@/services/mockAuthService';
import { getEmailError, getNewPasswordError, getRequiredError } from '@/utils/validators';
import { useGoBack } from '@/hooks/useBackNavigation';

type FieldName = 'fullName' | 'email' | 'password';

const SignUpScreen: React.FC = () => {
  const goBack = useGoBack('/(auth)/welcome');
  const [fullName, setFullName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [agreed, setAgreed] = useState(false);
  const [fieldErrors, setFieldErrors] = useState<Partial<Record<FieldName, string>>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const canSubmit = fullName.trim().length > 0 && email.trim().length > 0 && password.length > 0 && agreed;

  const setField = (field: FieldName, value: string) => {
    if (field === 'fullName') setFullName(value);
    if (field === 'email') setEmail(value);
    if (field === 'password') setPassword(value);
    setFieldErrors((prev) => ({ ...prev, [field]: undefined }));
  };

  const handleSubmit = async () => {
    const errors: Partial<Record<FieldName, string>> = {
      fullName: getRequiredError(fullName, 'full name') ?? undefined,
      email: getEmailError(email) ?? undefined,
      password: getNewPasswordError(password) ?? undefined,
    };
    setFieldErrors(errors);
    setFormError(null);
    if (Object.values(errors).some(Boolean) || !agreed) return;

    setSubmitting(true);
    try {
      const { email: confirmedEmail } = await mockAuthService.signUp({ fullName, email, password });
      router.push({ pathname: '/(auth)/verify-email', params: { email: confirmedEmail } });
    } catch (error) {
      setFormError(error instanceof MockAuthError ? error.message : 'Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <AuthScreenLayout
      title="Create an account"
      onBack={goBack}
      footer={
        <>
          <Button
            title="Create account"
            onPress={handleSubmit}
            loading={submitting}
            disabled={!canSubmit}
          />
          <Button
            title="Already have an account? Log in"
            variant="outline"
            onPress={() => router.dismissTo('/(auth)/login')}
          />
        </>
      }
    >
      <BrandMark />
      <AppText variant="subheading16">A fresh start for your finances</AppText>

      {formError ? <FeedbackBanner tone="error" title="Could not sign up" message={formError} /> : null}

      <Input
        label="Full name"
        placeholder="Enter your name"
        value={fullName}
        onChangeText={(value) => setField('fullName', value)}
        hasError={!!fieldErrors.fullName}
        errorMessage={fieldErrors.fullName}
        autoCapitalize="words"
      />
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
        placeholder="Create a password"
        value={password}
        onChangeText={(value) => setField('password', value)}
        hasError={!!fieldErrors.password}
        errorMessage={fieldErrors.password}
        hint={fieldErrors.password ? undefined : 'Use at least 8 characters, including a number and a capital letter.'}
        secureTextEntry
      />

      <ConsentCheckboxCard
        title="I agree to the Terms & Privacy Policy"
        description="Consent required before creating an account"
        checked={agreed}
        onToggle={setAgreed}
      />

      <AppText variant="body12" color={colors.text.secondary}>
        Static design preview only. No account, sign-in or email action is performed.
      </AppText>
    </AuthScreenLayout>
  );
};

export default SignUpScreen;
