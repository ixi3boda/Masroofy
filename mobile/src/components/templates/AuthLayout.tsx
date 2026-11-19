import React, { ReactNode } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ViewStyle,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { BrandHeader } from '@/components/organisms';

interface AuthLayoutProps {
  children: ReactNode;
  footer?: ReactNode;
  title?: string;
  showBack?: boolean;
  onBack?: () => void;
  scrollable?: boolean;
  style?: ViewStyle;
}

export const AuthLayout: React.FC<AuthLayoutProps> = ({
  children,
  footer,
  title,
  showBack = false,
  onBack,
  scrollable = true,
  style,
}) => {
  const contentArea = scrollable ? (
    <ScrollView
      style={styles.flex}
      showsVerticalScrollIndicator={false}
      contentContainerStyle={styles.scrollContent}
      keyboardShouldPersistTaps="handled"
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.flex, styles.scrollContent]}>{children}</View>
  );

  return (
    <SafeAreaView style={[styles.root, style]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        <BrandHeader title={title} showBack={showBack} onBack={onBack} />
        {contentArea}
        {footer ? <View style={styles.footer}>{footer}</View> : null}
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  root: {
    flex: 1,
    backgroundColor: '#F5F6F7',
  },
  flex: {
    flex: 1,
  },
  scrollContent: {
    paddingHorizontal: 16,
    paddingTop: 24,
  },
  footer: {
    paddingHorizontal: 16,
    paddingBottom: 16,
  },
});

export default AuthLayout;
