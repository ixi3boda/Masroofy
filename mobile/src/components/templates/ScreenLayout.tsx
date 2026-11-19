import React, { ReactNode } from 'react';
import {
  View,
  ScrollView,
  KeyboardAvoidingView,
  Platform,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';

interface ScreenLayoutProps {
  children: ReactNode;
  header?: ReactNode;
  footer?: ReactNode;
  backgroundColor?: string;
  scrollable?: boolean;
  keyboardAvoiding?: boolean;
  safeArea?: boolean;
  contentPadding?: number;
  style?: ViewStyle;
  contentContainerStyle?: ViewStyle;
}

export const ScreenLayout: React.FC<ScreenLayoutProps> = ({
  children,
  header,
  footer,
  backgroundColor = '#F5F6F7',
  scrollable = false,
  keyboardAvoiding = false,
  safeArea = false,
  contentPadding = 16,
  style,
  contentContainerStyle,
}) => {
  const Wrapper = safeArea ? SafeAreaView : View;

  const contentArea = scrollable ? (
    <ScrollView
      style={styles.flex}
      showsVerticalScrollIndicator={false}
      contentContainerStyle={[
        { paddingHorizontal: contentPadding },
        contentContainerStyle,
      ]}
    >
      {children}
    </ScrollView>
  ) : (
    <View
      style={[
        styles.flex,
        { paddingHorizontal: contentPadding },
        contentContainerStyle,
      ]}
    >
      {children}
    </View>
  );

  const inner = (
    <Wrapper style={[styles.flex, { backgroundColor }, style]}>
      {header ? <View>{header}</View> : null}
      {contentArea}
      {footer ? <View>{footer}</View> : null}
    </Wrapper>
  );

  if (keyboardAvoiding) {
    return (
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : 'height'}
      >
        {inner}
      </KeyboardAvoidingView>
    );
  }

  return inner;
};

const styles = StyleSheet.create({
  flex: {
    flex: 1,
  },
});

export default ScreenLayout;
