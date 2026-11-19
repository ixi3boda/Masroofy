import React, { ReactNode } from 'react';
import { View, TouchableOpacity, StyleSheet, ViewStyle } from 'react-native';
import Text from '@/components/atoms/Text';

export interface AppHeaderProps {
  title: string;
  showBackButton?: boolean;
  onBack?: () => void;
  rightElement?: ReactNode;
  transparent?: boolean;
  style?: ViewStyle;
}

const AppHeader: React.FC<AppHeaderProps> = ({
  title,
  showBackButton = false,
  onBack,
  rightElement,
  transparent = false,
  style,
}) => {
  return (
    <View
      style={[
        styles.container,
        transparent ? styles.transparent : styles.defaultBg,
        style,
      ]}
    >
      {/* Left: back button or spacer */}
      <View style={styles.side}>
        {showBackButton && (
          <TouchableOpacity onPress={onBack} activeOpacity={0.7} style={styles.backBtn}>
            <Text variant="subheading18" color="#242D35">←</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Center: title */}
      <View style={styles.center}>
        <Text variant="subheading18" color="#242D35" align="center">
          {title}
        </Text>
      </View>

      {/* Right element or spacer */}
      <View style={styles.side}>
        {rightElement ?? null}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    height: 52,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
  },
  defaultBg: {
    backgroundColor: 'rgba(255,255,255,0.75)',
  },
  transparent: {
    backgroundColor: 'transparent',
  },
  side: {
    width: 44,
    alignItems: 'center',
    justifyContent: 'center',
  },
  center: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
  },
  backBtn: {
    padding: 4,
  },
});

export default AppHeader;
