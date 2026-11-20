import React, { ReactNode } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing } from '@theme/index';
import AppHeader from '@components/organisms/AppHeader';

export interface AppScreenLayoutProps {
  title: string;
  /** Trailing header control, e.g. a profile button. */
  headerRight?: ReactNode;
  /** Persistent bar pinned below the scroll area (handles its own bottom inset). */
  bottomBar?: ReactNode;
  /** Screen sections, stacked in a vertical scrollable column. */
  children: ReactNode;
}

const AppScreenLayout: React.FC<AppScreenLayoutProps> = ({ title, headerRight, bottomBar, children }) => (
  <SafeAreaView style={styles.safeArea} edges={['top']}>
    <AppHeader title={title} right={headerRight} />
    <View style={styles.body}>
      <ScrollView contentContainerStyle={styles.content} showsVerticalScrollIndicator={false}>
        {children}
      </ScrollView>
    </View>
    {bottomBar}
  </SafeAreaView>
);

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.surface },
  body: { flex: 1, backgroundColor: colors.background },
  content: {
    gap: spacing.xxl,
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xxl,
    paddingBottom: spacing.xxxl,
  },
});

export default AppScreenLayout;
