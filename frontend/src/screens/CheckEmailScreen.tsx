import React, { useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import Icon from '@components/atoms/Icon';
import StateSummary from '@components/molecules/StateSummary';
import EmailPreviewRow from '@components/molecules/EmailPreviewRow';
import SummaryCard from '@components/molecules/SummaryCard';
import OtpCodeField from '@components/molecules/OtpCodeField';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import AuthScreenLayout from '@components/templates/AuthScreenLayout';
import { mockAuthService, MockAuthError, MOCK_VERIFICATION_CODE } from '@/services/mockAuthService';
import { useCountdown } from '@/hooks/useCountdown';

const CODE_LENGTH = 6;
const RESEND_COOLDOWN_SECONDS = 30;

const CheckEmailScreen: React.FC = () => {
  const { email = '' } = useLocalSearchParams<{ email?: string }>();
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const { remaining, isDone, restart } = useCountdown(RESEND_COOLDOWN_SECONDS);

  const code = digits.join('');

  const handleVerify = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await mockAuthService.verifyResetCode(email, code);
      router.push({ pathname: '/(auth)/reset-password', params: { email } });
    } catch (err) {
      setError(err instanceof MockAuthError ? err.message : 'Something went wrong. Try again.');
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await mockAuthService.resendResetCode(email);
      restart();
    } finally {
      setResending(false);
    }
  };

  return (
    <AuthScreenLayout
      title="Check your email"
      onBack={() => router.back()}
      footer={<Button title="Verify Code" onPress={handleVerify} loading={submitting} disabled={code.length < CODE_LENGTH} />}
    >
      <Chip label="Confirmation preview" tone="info" />

      <StateSummary
        icon={<Icon name="mail-check" size={42} color={colors.text.inverse} />}
        heading="Check your email"
        description="We have sent a 6-digit password reset code to your email. Enter the code below to reset your password."
      />
      <EmailPreviewRow email={email} caption="This is the address the request preview is using." />

      <SummaryCard
        heading="What to do next"
        rows={[
          'Look in your inbox and spam folder, then follow the reset instructions.',
          'If you entered the wrong address, return to the request screen.',
        ]}
      />

      <AppText variant="body14">Enter 6-digit code</AppText>
      <OtpCodeField length={CODE_LENGTH} value={digits} onChange={setDigits} />

      {error ? <FeedbackBanner tone="error" title="Could not verify" message={error} /> : null}

      <Button
        title={isDone ? "Didn't receive the email? Resend code" : `Resend code in ${remaining}s`}
        variant="outline"
        onPress={handleResend}
        disabled={!isDone}
        loading={resending}
      />

      <FeedbackBanner
        tone="info"
        title="No email sent"
        message={`This design shows the request confirmation only. It has not checked an address or sent a message. Use ${MOCK_VERIFICATION_CODE} in this preview.`}
      />
    </AuthScreenLayout>
  );
};

export default CheckEmailScreen;
