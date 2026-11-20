import React, { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';

export interface AppHeaderProps {
  title: string;
  /** Trailing control, e.g. a profile IconButton. */
  right?: ReactNode;
}

const AppHeader: React.FC<AppHeaderProps> = ({ title, right }) => (
  <View style={styles.container}>
    <AppText variant="subheading18" accessibilityRole="header" numberOfLines={1} style={styles.title}>
      {title}
    </AppText>
    {right}
  </View>
);

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 20,
    minHeight: 52,
    paddingHorizontal: 16,
    paddingVertical: 6,
    backgroundColor: colors.surface,
  },
  title: { flex: 1 },
});

export default AppHeader;
