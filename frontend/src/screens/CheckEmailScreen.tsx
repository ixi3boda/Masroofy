import React, { useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import StateSummary from '@components/molecules/StateSummary';
import EmailPreviewRow from '@components/molecules/EmailPreviewRow';
import OtpCodeField from '@components/molecules/OtpCodeField';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import SummaryCard from '@components/organisms/SummaryCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { RESEND_COOLDOWN_SECONDS, VERIFICATION_CODE_LENGTH } from '@/constants/app';
import { MOCK_VERIFICATION_CODE } from '@/mocks';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { strings } from '@/strings';
import { getErrorMessage } from '@/utils/errors';
import { useCountdown } from '@/hooks/useCountdown';
import { useGoBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.checkEmail;

const CheckEmailScreen: React.FC = () => {
  const { email = '' } = useLocalSearchParams<{ email?: string }>();
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [resending, setResending] = useState(false);
  const { remaining, isDone, restart } = useCountdown(RESEND_COOLDOWN_SECONDS);
  const goBack = useGoBack(ROUTES.auth.forgotPassword);

  const code = digits.join('');

  const handleVerify = async () => {
    setError(null);
    setSubmitting(true);
    try {
      await authService.verifyResetCode(email, code);
      router.push({ pathname: ROUTES.auth.resetPassword, params: { email } });
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setResending(true);
    try {
      await authService.resendResetCode(email);
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
      <Chip label={copy.previewChip} tone="info" />

      <StateSummary icon="mail-check" heading={copy.heading} description={copy.description} />
      <EmailPreviewRow email={email} caption={copy.emailCaption} />

      <SummaryCard heading={copy.nextStepsHeading} rows={copy.nextSteps} />

      <AppText variant="body14">{copy.codeLabel}</AppText>
      <OtpCodeField length={VERIFICATION_CODE_LENGTH} value={digits} onChange={setDigits} />

      {error ? <FeedbackBanner tone="error" title={copy.errorTitle} message={error} /> : null}

      <Button
        title={isDone ? copy.resend : strings.common.resendCodeIn(remaining)}
        variant="outline"
        onPress={handleResend}
        disabled={!isDone}
        loading={resending}
      />

      <FeedbackBanner tone="info" title={copy.previewTitle} message={copy.previewMessage(MOCK_VERIFICATION_CODE)} />
    </ScreenLayout>
  );
};

export default CheckEmailScreen;
