import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon, { IconName } from '@components/atoms/Icon';
import IconBadge, { IconBadgeTone } from '@components/atoms/IconBadge';

export interface StateSummaryProps {
  icon: IconName;
  heading: string;
  description: string;
  /** e.g. a masked email shown under the description. */
  value?: string;
  /** brand = success/neutral state · error = failure or empty import. */
  tone?: IconBadgeTone;
  /**
   * hero = full-screen state with a large badge (saved, empty, error screens)
   * compact = small in-card note, e.g. "Stock history unavailable".
   */
  size?: 'hero' | 'compact';
  style?: StyleProp<ViewStyle>;
}

const StateSummary: React.FC<StateSummaryProps> = ({
  icon,
  heading,
  description,
  value,
  tone = 'brand',
  size = 'hero',
  style,
}) => {
  if (size === 'compact') {
    return (
      <View style={[styles.compact, style]}>
        <Icon name={icon} size={28} color={colors.text.secondary} style={styles.compactIcon} />
        <AppText variant="subheading14">{heading}</AppText>
        <AppText variant="body14" color={colors.text.secondary}>
          {description}
        </AppText>
      </View>
    );
  }

  return (
    <View style={[styles.hero, style]}>
      <IconBadge size="lg" tone={tone}>
        <Icon name={icon} size={42} color={tone === 'error' ? colors.tone.error.foreground : colors.text.inverse} />
      </IconBadge>
      <AppText variant="h2" align="center" accessibilityRole="header">
        {heading}
      </AppText>
      <AppText variant="body14" color={colors.text.secondary} align="center">
        {description}
      </AppText>
      {value ? <AppText variant="subheading16">{value}</AppText> : null}
    </View>
  );
};

const styles = StyleSheet.create({
  hero: {
    width: '100%',
    alignItems: 'center',
    gap: 20,
    paddingVertical: 24,
  },
  compact: { width: '100%', gap: 8, paddingVertical: 8 },
  compactIcon: { alignSelf: 'center', marginBottom: 4 },
});

export default StateSummary;
