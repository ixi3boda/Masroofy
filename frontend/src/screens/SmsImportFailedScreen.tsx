import React, { useState } from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Input from '@components/atoms/Input';
import DividedCard from '@components/molecules/DividedCard';
import FeedbackBanner from '@components/molecules/FeedbackBanner';
import StateSummary from '@components/molecules/StateSummary';
import ScreenLayout from '@components/templates/ScreenLayout';
import { useGoBack } from '@/hooks/useBackNavigation';
import { ROUTES } from '@/navigation/routes';
import { smsService } from '@/services/smsService';
import { strings } from '@/strings';

const copy = strings.sms.importFailed;

/**
 * 04-10 · Empty or failed import: nothing was read, so the user pastes the message again.
 * It takes the import form's place in the stack, so back and Cancel both return to Bank Messages.
 */
const SmsImportFailedScreen: React.FC = () => {
  const goBack = useGoBack(ROUTES.sms.messages);
  const [text, setText] = useState('');
  const [unreadable, setUnreadable] = useState(false);
  const [loading, setLoading] = useState(false);

  const changeText = (value: string) => {
    setText(value);
    setUnreadable(false);
  };

  const submit = async () => {
    setLoading(true);
    try {
      const message = await smsService.importMessage(text);
      if (message) {
        router.replace({ pathname: ROUTES.sms.processing, params: { id: message.id } });
      } else {
        setUnreadable(true);
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
          <Button title={copy.share} variant="outline" onPress={() => changeText(smsService.getSharedText())} />
          <Button title={copy.cancel} variant="outline" onPress={goBack} />
        </>
      }
    >
      <StateSummary tone="error" icon="message-warning" heading={copy.heading} description={copy.description} />

      <DividedCard title={copy.tryHeading}>
        <AppText variant="body14" color={colors.text.secondary}>
          {copy.tryMessage}
        </AppText>
        <Input
          label={copy.fieldLabel}
          placeholder={copy.fieldPlaceholder}
          hint={copy.fieldHint}
          hasError={unreadable}
          errorMessage={copy.fieldError}
          value={text}
          onChangeText={changeText}
          multiline
        />
      </DividedCard>

      <FeedbackBanner title={copy.bannerTitle} message={copy.bannerMessage} />
    </ScreenLayout>
  );
};

export default SmsImportFailedScreen;
