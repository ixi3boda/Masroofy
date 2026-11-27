import React, { useState } from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import OptionCard from '@components/molecules/OptionCard';
import SummaryCard from '@components/organisms/SummaryCard';
import ScreenLayout from '@components/templates/ScreenLayout';
import { isMockSource } from '@/config/env';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { smsService } from '@/services/smsService';
import { strings } from '@/strings';

const copy = strings.sms.import;

/** 04-01 · Import Bank SMS: paste (or share) one message and consent to reviewing it. */
const SmsImportScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.sms.messages);
  const [text, setText] = useState('');
  const [consented, setConsented] = useState(false);
  const [consentMissing, setConsentMissing] = useState(false);
  const [loading, setLoading] = useState(false);

  const toggleConsent = () => {
    setConsented((value) => !value);
    setConsentMissing(false);
  };

  const submit = async () => {
    if (!consented) {
      setConsentMissing(true);
      return;
    }
    setLoading(true);
    try {
      const message = await smsService.importMessage(text);
      // Replace, not push: once imported, back from any later step returns to Bank Messages, never to this form.
      if (message) {
        router.replace({ pathname: ROUTES.sms.processing, params: { id: message.id } });
      } else {
        router.replace(ROUTES.sms.importFailed);
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <ScreenLayout
      title={copy.title}
      onBack={goBack}
      footer={
        <>
          <Button title={copy.submit} loading={loading} onPress={submit} />
          <Button title={copy.share} variant="outline" onPress={() => setText(smsService.getSharedText())} />
          <Button title={copy.cancel} variant="outline" onPress={goBack} />
        </>
      }
    >
      <FeedbackBanner title={copy.guidanceTitle} message={copy.guidanceMessage} />

      <DividedCard title={copy.pasteHeading}>
        <Input
          label={copy.fieldLabel}
          placeholder={copy.fieldPlaceholder}
          hint={copy.fieldHint}
          value={text}
          onChangeText={setText}
          multiline
        />
      </DividedCard>

      <OptionCard
        kind="checkbox"
        title={copy.consentTitle}
        description={copy.consentDescription}
        selected={consented}
        onPress={toggleConsent}
      />
      {consentMissing ? <FeedbackBanner tone="error" title={copy.consentRequired} /> : null}

      <SummaryCard heading={copy.howHeading} rows={copy.howSteps} />

      {isMockSource('sms') ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {copy.previewNote}
        </AppText>
      ) : null}
    </ScreenLayout>
  );
};

export default SmsImportScreen;
