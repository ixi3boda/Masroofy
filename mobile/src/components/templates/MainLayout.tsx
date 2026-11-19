import React, { ReactNode } from 'react';
import {
  View,
  ScrollView,
  StyleSheet,
  ViewStyle,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { BottomTabBar } from '@/components/organisms';

interface MainLayoutProps {
  children: ReactNode;
  activeTab: 'home' | 'savings' | 'reminders' | 'settings';
  onTabPress: (tab: string) => void;
  header?: ReactNode;
  scrollable?: boolean;
  style?: ViewStyle;
}

export const MainLayout: React.FC<MainLayoutProps> = ({
  children,
  activeTab,
  onTabPress,
  header,
  scrollable = true,
  style,
}) => {
  const contentArea = scrollable ? (
    <ScrollView
      style={styles.flex}
      showsVerticalScrollIndicator={false}
      contentContainerStyle={styles.scrollContent}
    >
      {children}
    </ScrollView>
  ) : (
    <View style={[styles.flex, styles.scrollContent]}>{children}</View>
  );

  return (
    <SafeAreaView style={[styles.root, style]}>
      {header ? <View>{header}</View> : null}
      {contentArea}
      <BottomTabBar activeTab={activeTab} onTabPress={onTabPress} />
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
  },
});

export default MainLayout;
