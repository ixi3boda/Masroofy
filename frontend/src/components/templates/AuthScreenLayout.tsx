import React, { ReactNode } from 'react';
import {
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing } from '@theme/index';
import AuthHeader from '@components/organisms/AuthHeader';

export interface AuthScreenLayoutProps {
  title: string;
  onBack?: () => void;
  /** Replaces the back arrow, e.g. a "Cancel" link. */
  headerLeft?: ReactNode;
  /** Trailing header action, e.g. a compact "Save Changes" button. */
  headerRight?: ReactNode;
  /** Primary screen content, laid out in a vertical, scrollable column. */
  children: ReactNode;
  /** Sticky action buttons pinned to the bottom of the screen. */
  footer?: ReactNode;
}

const AuthScreenLayout: React.FC<AuthScreenLayoutProps> = ({ title, onBack, headerLeft, headerRight, children, footer }) => {
  return (
    <SafeAreaView style={styles.safeArea} edges={['top', 'bottom']}>
      <AuthHeader title={title} onBack={onBack} left={headerLeft} right={headerRight} />
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
      >
        <ScrollView
          contentContainerStyle={styles.content}
          keyboardShouldPersistTaps="handled"
        >
          {children}
        </ScrollView>
        {footer ? <View style={styles.footer}>{footer}</View> : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  safeArea: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  content: {
    gap: spacing.xl,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.xxl,
  },
  footer: {
    gap: spacing.sm,
    paddingHorizontal: spacing.lg,
    paddingVertical: spacing.sm,
  },
});

export default AuthScreenLayout;
