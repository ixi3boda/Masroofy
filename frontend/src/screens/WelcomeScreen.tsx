import React from 'react';
import { StyleSheet, View } from 'react-native';
import { router } from 'expo-router';
import { colors, spacing } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Chip from '@components/atoms/Chip';
import { IconName } from '@components/atoms/Icon';
import IconTile from '@components/atoms/IconTile';
import BrandMark from '@components/molecules/BrandMark';
import DividedCard from '@components/molecules/DividedCard';
import ListRow from '@components/molecules/ListRow';
import ScreenLayout from '@components/templates/ScreenLayout';
import { ROUTES } from '@/navigation/routes';
import { strings } from '@/strings';

const copy = strings.auth.welcome;

const FEATURES: { key: keyof typeof copy.features; icon: IconName }[] = [
  { key: 'track', icon: 'wallet' },
  { key: 'plan', icon: 'chart-column' },
  { key: 'review', icon: 'shield-check' },
];

/**
 * First screen of the app: no header bar, a centered brand hero, three
 * scannable value points, and the two entry actions pinned to the bottom.
 */
const WelcomeScreen: React.FC = () => (
  <ScreenLayout
    gap={spacing.xxl}
    footer={
      <>
        <Button title={copy.createAccount} onPress={() => router.push(ROUTES.auth.signUp)} />
        <Button title={copy.logIn} variant="outline" onPress={() => router.push(ROUTES.auth.login)} />
      </>
    }
  >
    <View style={styles.hero}>
      <BrandMark />
      <AppText variant="h1" align="center" accessibilityRole="header">
        {copy.heading}
      </AppText>
      <AppText variant="body14" color={colors.text.secondary} align="center">
        {copy.intro}
      </AppText>
      <Chip label={copy.regionChip} tone="info" style={styles.chip} />
    </View>

    <DividedCard>
      {FEATURES.map(({ key, icon }) => (
        <ListRow
          key={key}
          leading={<IconTile name={icon} tone="brand" />}
          title={copy.features[key].title}
          subtitle={copy.features[key].description}
        />
      ))}
    </DividedCard>
  </ScreenLayout>
);

const styles = StyleSheet.create({
  hero: { alignItems: 'center', gap: spacing.md, paddingTop: spacing.xl },
  chip: { alignSelf: 'center', marginTop: spacing.xs },
});

export default WelcomeScreen;
