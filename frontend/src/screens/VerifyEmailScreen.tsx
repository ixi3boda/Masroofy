import React, { useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import StateSummary from '@components/molecules/StateSummary';
import OtpCodeField from '@components/molecules/OtpCodeField';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ScreenLayout from '@components/templates/ScreenLayout';
import { mockAuthService, MockAuthError, MOCK_VERIFICATION_CODE } from '@/services/mockAuthService';
import { maskEmail } from '@/utils/maskEmail';
import { useCountdown } from '@/hooks/useCountdown';
import { useGoBack } from '@/hooks/useBackNavigation';
import { useSessionStore } from '@/store/sessionStore';

const CODE_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 30;

const VerifyEmailScreen: React.FC = () => {
  const { email = '' } = useLocalSearchParams<{ email?: string }>();
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const { remaining, isDone, restart } = useCountdown(RESEND_COOLDOWN_SECONDS);
  const signIn = useSessionStore((state) => state.signIn);
  const goBack = useGoBack('/(auth)/sign-up');

  const code = digits.join('');

  const handleVerify = async () => {
    setError(null);
    setSubmitting(true);
    try {
      signIn(await mockAuthService.verifySignUpCode(email, code));
      router.replace('/(app)/home');
    } catch (err) {
      setError(err instanceof MockAuthError ? err.message : 'Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await mockAuthService.resendSignUpCode(email);
      restart();
    } finally {
      setResending(false);
    }
  };

  return (
    <ScreenLayout
      title="Verify signup email"
      onBack={goBack}
      footer={
        <Button
          title="Verify email"
          onPress={handleVerify}
          loading={submitting}
          disabled={code.length < CODE_LENGTH}
        />
      }
    >
      <StateSummary
        icon="mail-check"
        heading="One step to get started"
        description="Confirm your email to finish signing up for Masroofy."
        value={maskEmail(email)}
      />

      <AppText variant="body12">Six-digit verification code</AppText>
      <OtpCodeField length={CODE_LENGTH} value={digits} onChange={setDigits} filled />

      {error ? <FeedbackBanner tone="error" title="Could not verify" message={error} /> : (
        <AppText variant="body12" color={colors.text.secondary}>
          Enter the code for your new account, not a password-reset code.
        </AppText>
      )}

      <Button
        title={isDone ? 'Resend code' : `Resend code in ${remaining}s`}
        variant="outline"
        onPress={handleResend}
        disabled={!isDone}
        loading={resending}
      />

      <Chip label="Illustrative preview" tone="info" />
      <AppText variant="body12" color={colors.text.secondary}>
        No verification email has been sent. Use {MOCK_VERIFICATION_CODE} in this preview.
      </AppText>
    </ScreenLayout>
  );
};

export default VerifyEmailScreen;
