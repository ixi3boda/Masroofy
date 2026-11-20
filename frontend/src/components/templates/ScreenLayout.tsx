import React, { ReactNode } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing } from '@theme/index';
import ScreenHeader, { ScreenHeaderProps } from '@components/organisms/ScreenHeader';

export interface ScreenLayoutProps {
  title: string;
  onBack?: () => void;
  headerLeft?: ScreenHeaderProps['left'];
  headerRight?: ScreenHeaderProps['right'];
  titleAlign?: ScreenHeaderProps['titleAlign'];
  /** Screen content, stacked in a vertical scrollable column. */
  children: ReactNode;
  /** Sticky action buttons pinned above the bottom edge (stack screens). */
  footer?: ReactNode;
  /** Persistent tab bar (top-level screens); it handles the bottom safe-area inset itself. */
  bottomBar?: ReactNode;
  /** Vertical space between sections; defaults to the 20px used by most screens. */
  gap?: number;
}

/** The one page shell: header → keyboard-aware scroll body → optional footer and/or tab bar. */
const ScreenLayout: React.FC<ScreenLayoutProps> = ({
  title,
  onBack,
  headerLeft,
  headerRight,
  titleAlign,
  children,
  footer,
  bottomBar,
  gap = spacing.xl,
}) => (
  <SafeAreaView style={styles.safeArea} edges={bottomBar ? ['top'] : ['top', 'bottom']}>
    <ScreenHeader title={title} onBack={onBack} left={headerLeft} right={headerRight} titleAlign={titleAlign} />
    <KeyboardAvoidingView style={styles.body} behavior={Platform.OS === 'ios' ? 'padding' : undefined}>
      <ScrollView
        contentContainerStyle={[styles.content, { gap }]}
        keyboardShouldPersistTaps="handled"
        showsVerticalScrollIndicator={false}
      >
        {children}
      </ScrollView>
      {footer ? <View style={styles.footer}>{footer}</View> : null}
    </KeyboardAvoidingView>
    {bottomBar}
  </SafeAreaView>
);

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.surface },
  body: { flex: 1, backgroundColor: colors.background },
  content: {
    paddingHorizontal: spacing.lg,
    paddingTop: spacing.xxl,
    paddingBottom: spacing.xxxl,
  },
  footer: {
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
});

export default ScreenLayout;
