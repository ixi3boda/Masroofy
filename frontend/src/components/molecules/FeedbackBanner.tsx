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
  warning: 'circle-alert',
};

export interface FeedbackBannerProps {
  tone?: ChipTone;
  title: string;
  /** Optional detail line; omit for a single-line inline message (e.g. field validation). */
  message?: string;
  /** Overrides the tone's default icon (e.g. `link` for linked-evidence notes). */
  icon?: IconName;
  style?: StyleProp<ViewStyle>;
}

const FeedbackBanner: React.FC<FeedbackBannerProps> = ({ tone = 'info', title, message, icon, style }) => {
  const { background, foreground } = colors.tone[tone];

  return (
    <View
      style={[styles.container, { backgroundColor: background }, style]}
      accessibilityRole={tone === 'error' ? 'alert' : undefined}
    >
      <Icon name={icon ?? TONE_ICON[tone]} size={20} color={foreground} />
      <View style={styles.copy}>
        <AppText variant="subheading13" color={foreground}>
          {title}
        </AppText>
        {message ? (
          <AppText variant="body12" color={foreground}>
            {message}
          </AppText>
        ) : null}
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
  copy: { flex: 1, gap: 4, justifyContent: 'center' },
});

export default FeedbackBanner;
