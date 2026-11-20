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
import { isMockSource } from '@/config/env';
import { RESEND_COOLDOWN_SECONDS, VERIFICATION_CODE_LENGTH } from '@/constants/app';
import { MOCK_VERIFICATION_CODE } from '@/mocks';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { usePasswordResetStore } from '@/store/passwordResetStore';
import { strings } from '@/strings';
import { getErrorMessage, isApiError } from '@/utils/errors';
import { useResendCode } from '@/hooks/useResendCode';
import { useGoBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.checkEmail;

/** Params: `email`; `resendIn` (seconds until Resend, from the forgot-password request). */
const CheckEmailScreen: React.FC = () => {
  const { email = '', resendIn } = useLocalSearchParams<{ email?: string; resendIn?: string }>();
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const resendCode = useResendCode(
    () => authService.resendResetCode(email),
    Number(resendIn) || RESEND_COOLDOWN_SECONDS
  );
  const setResetToken = usePasswordResetStore((state) => state.setResetToken);
  const goBack = useGoBack(ROUTES.auth.forgotPassword);
  const isMock = isMockSource('auth');

  const code = digits.join('');

  const handleVerify = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const { resetToken } = await authService.verifyResetCode(email, code);
      setResetToken(resetToken);
      router.push(ROUTES.auth.resetPassword);
    } catch (err) {
      if (isApiError(err, 'INVALID_CODE')) setDigits([]);
      setError(getErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  };

  const handleResend = async () => {
    setError(null);
    try {
      if (await resendCode.resend()) setDigits([]);
    } catch (err) {
      setError(getErrorMessage(err));
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
      {isMock ? <Chip label={copy.previewChip} tone="info" /> : null}

      <StateSummary icon="mail-check" heading={copy.heading} description={copy.description} />
      <EmailPreviewRow email={email} caption={copy.emailCaption} />

      <SummaryCard heading={copy.nextStepsHeading} rows={copy.nextSteps} />

      <AppText variant="body14">{copy.codeLabel}</AppText>
      <OtpCodeField length={VERIFICATION_CODE_LENGTH} value={digits} onChange={setDigits} />

      {error ? <FeedbackBanner tone="error" title={copy.errorTitle} message={error} /> : null}

      <Button
        title={resendCode.isDone ? copy.resend : strings.common.resendCodeIn(resendCode.remaining)}
        variant="outline"
        onPress={handleResend}
        disabled={!resendCode.isDone}
        loading={resendCode.resending}
      />

      {isMock ? (
        <FeedbackBanner tone="info" title={copy.previewTitle} message={copy.previewMessage(MOCK_VERIFICATION_CODE)} />
      ) : null}
    </ScreenLayout>
  );
};

export default CheckEmailScreen;
