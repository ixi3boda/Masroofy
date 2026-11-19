import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon, { IconName } from '@components/atoms/Icon';
import { ChipTone } from '@components/atoms/Chip';

const TONE_ICON: Record<ChipTone, IconName> = {
  info: 'info',
  success: 'circle-check',
  error: 'triangle-alert',
};

export interface FeedbackBannerProps {
  tone?: ChipTone;
  title: string;
  message: string;
  style?: StyleProp<ViewStyle>;
}

const FeedbackBanner: React.FC<FeedbackBannerProps> = ({ tone = 'info', title, message, style }) => {
  const { background, foreground } = colors.tone[tone];

  return (
    <View style={[styles.container, { backgroundColor: background }, style]}>
      <Icon name={TONE_ICON[tone]} size={20} color={foreground} />
      <View style={styles.copy}>
        <AppText variant="subheading13" color={foreground}>
          {title}
        </AppText>
        <AppText variant="body12" color={foreground}>
          {message}
        </AppText>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
    flexDirection: 'row',
    gap: 10,
    padding: 14,
    borderRadius: radii.md,
  },
  copy: { flex: 1, gap: 4 },
});

export default FeedbackBanner;
