import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import IconBadge from '@components/atoms/IconBadge';

export interface StateSummaryProps {
  icon: ReactNode;
  heading: string;
  description: string;
  /** e.g. a masked email shown under the description. */
  value?: string;
  style?: StyleProp<ViewStyle>;
}

const StateSummary: React.FC<StateSummaryProps> = ({ icon, heading, description, value, style }) => (
  <View style={[styles.container, style]}>
    <IconBadge size="lg">{icon}</IconBadge>
    <AppText variant="h2" align="center">
      {heading}
    </AppText>
    <AppText variant="body14" color={colors.text.secondary} align="center">
      {description}
    </AppText>
    {value ? <AppText variant="subheading16">{value}</AppText> : null}
  </View>
);

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignItems: 'center',
    gap: 20,
    paddingVertical: 24,
  },
});

export default StateSummary;
