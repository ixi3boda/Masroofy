import React from 'react';
import { router } from 'expo-router';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import BrandMark from '@components/molecules/BrandMark';
import SummaryCard from '@components/molecules/SummaryCard';
import AuthScreenLayout from '@components/templates/AuthScreenLayout';

const WelcomeScreen: React.FC = () => {
  return (
    <AuthScreenLayout
      title="Welcome to Masroofy"
      footer={
        <>
          <Button title="Create an account" onPress={() => router.push('/(auth)/sign-up')} />
          <Button title="Log in" variant="outline" onPress={() => router.push('/(auth)/login')} />
        </>
      }
    >
      <BrandMark />

      <AppText variant="h1">Your money, a little clearer.</AppText>
      <AppText variant="body14" color={colors.text.secondary}>
        Keep everyday spending, salary plans and budgets together. Made for life in Egypt, with
        amounts in EGP.
      </AppText>

      <SummaryCard
        heading="Start with the everyday"
        rowVariant="subheading14"
        rows={[
          'Track what comes in and goes out',
          'Plan your month with confidence',
          'Review every imported detail',
        ]}
      />

      <AppText variant="body12" color={colors.text.secondary}>
        Static design preview only. No account, sign-in or email action is performed.
      </AppText>
    </AuthScreenLayout>
  );
};

export default WelcomeScreen;
