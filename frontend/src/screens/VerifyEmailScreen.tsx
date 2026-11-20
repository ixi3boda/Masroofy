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
import { RESEND_COOLDOWN_SECONDS, VERIFICATION_CODE_LENGTH } from '@/constants/app';
import { MOCK_VERIFICATION_CODE } from '@/mocks';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { useSessionStore } from '@/store/sessionStore';
import { strings } from '@/strings';
import { getErrorMessage } from '@/utils/errors';
import { maskEmail } from '@/utils/maskEmail';
import { useCountdown } from '@/hooks/useCountdown';
import { useGoBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.verifyEmail;

const VerifyEmailScreen: React.FC = () => {
  const { email = '' } = useLocalSearchParams<{ email?: string }>();
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const { remaining, isDone, restart } = useCountdown(RESEND_COOLDOWN_SECONDS);
  const signIn = useSessionStore((state) => state.signIn);
  const goBack = useGoBack(ROUTES.auth.signUp);

  const code = digits.join('');

  const handleVerify = async () => {
    setError(null);
    setSubmitting(true);
    try {
      signIn(await authService.verifySignUpCode(email, code));
      router.replace(ROUTES.app.home);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await authService.resendSignUpCode(email);
      restart();
    } finally {
      setResending(false);
    }
  };

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <Button
          title={copy.submit}
          onPress={handleVerify}
          loading={submitting}
          disabled={code.length < VERIFICATION_CODE_LENGTH}
        />
      }
    >
      <StateSummary icon="mail-check" heading={copy.heading} description={copy.description} value={maskEmail(email)} />

      <AppText variant="body12">{copy.codeLabel}</AppText>
      <OtpCodeField length={VERIFICATION_CODE_LENGTH} value={digits} onChange={setDigits} filled />

      {error ? (
        <FeedbackBanner tone="error" title={copy.errorTitle} message={error} />
      ) : (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.codeHint}
        </AppText>
      )}

      <Button
        title={isDone ? strings.common.resendCode : strings.common.resendCodeIn(remaining)}
        variant="outline"
        onPress={handleResend}
        disabled={!isDone}
        loading={resending}
      />

      <Chip label={copy.previewChip} tone="info" />
      <AppText variant="body12" color={colors.text.secondary}>
        {copy.previewNotice(MOCK_VERIFICATION_CODE)}
      </AppText>
    </ScreenLayout>
  );
};

export default VerifyEmailScreen;
