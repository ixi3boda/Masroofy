import React, { useEffect, useState } from 'react';
import { router, useLocalSearchParams } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import StateSummary from '@components/molecules/StateSummary';
import OtpCodeField from '@components/molecules/OtpCodeField';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { RESEND_COOLDOWN_SECONDS, VERIFICATION_CODE_LENGTH } from '@/constants/app';
import { MOCK_VERIFICATION_CODE } from '@/mocks';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { strings } from '@/strings';
import { getErrorMessage, isApiError } from '@/utils/errors';
import { maskEmail } from '@/utils/maskEmail';
import { useResendCode } from '@/hooks/useResendCode';
import { useGoBack } from '@/hooks/useBackNavigation';

const copy = strings.auth.verifyEmail;

/**
 * Params: `email`; `resendIn` (seconds until Resend, from sign-up); `resend=1`
 * when opened from Login for an unverified email — login sends no code, so
 * this screen asks for one when it opens.
 */
const VerifyEmailScreen: React.FC = () => {
  const { email = '', resendIn, resend } = useLocalSearchParams<{ email?: string; resendIn?: string; resend?: string }>();
  const resendOnOpen = resend === '1';
  const [digits, setDigits] = useState<string[]>([]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const resendCode = useResendCode(
    () => authService.resendSignUpCode(email),
    resendOnOpen ? 0 : Number(resendIn) || RESEND_COOLDOWN_SECONDS
  );
  const goBack = useGoBack(ROUTES.auth.signUp);

  const code = digits.join('');

  const handleVerify = async () => {
    setError(null);
    setSubmitting(true);
    try {
      const { email: verifiedEmail } = await authService.verifySignUpCode(email, code);
      router.replace({ pathname: ROUTES.auth.login, params: { email: verifiedEmail } });
    } catch (err) {
      if (isApiError(err, 'EMAIL_ALREADY_VERIFIED')) {
        router.replace({ pathname: ROUTES.auth.login, params: { email } });
        return;
      }
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

  useEffect(() => {
    if (resendOnOpen) resendCode.resend().catch((err) => setError(getErrorMessage(err)));
    // Runs once when the screen opens.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

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
        title={resendCode.isDone ? strings.common.resendCode : strings.common.resendCodeIn(resendCode.remaining)}
        variant="outline"
        onPress={handleResend}
        disabled={!resendCode.isDone}
        loading={resendCode.resending}
      />

      {isMockSource('auth') ? (
        <>
          <Chip label={copy.previewChip} tone="info" />
          <AppText variant="body12" color={colors.text.secondary}>
            {copy.previewNotice(MOCK_VERIFICATION_CODE)}
          </AppText>
        </>
      ) : null}
    </ScreenLayout>
  );
};

export default VerifyEmailScreen;
