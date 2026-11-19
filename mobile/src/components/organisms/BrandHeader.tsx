import React from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
import Text from '@/components/atoms/Text';

export interface BrandHeaderProps {
  title?: string;
  showBack?: boolean;
  onBack?: () => void;
}

const BrandHeader: React.FC<BrandHeaderProps> = ({
  title = 'Welcome to Masroofy',
  showBack = false,
  onBack,
}) => {
  return (
    <View style={styles.wrapper}>
      {/* Status bar placeholder */}
      <View style={styles.statusBar} />

      {/* Navigation row */}
      <View style={styles.navRow}>
        <View style={styles.side}>
          {showBack && (
            <TouchableOpacity onPress={onBack} activeOpacity={0.7} style={styles.backBtn}>
              <Text variant="subheading18" color="#242D35">←</Text>
            </TouchableOpacity>
          )}
        </View>

        <View style={styles.center}>
          <Text variant="subheading18" color="#242D35" align="center">
            {title}
          </Text>
        </View>

        <View style={styles.side} />
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  wrapper: {
    backgroundColor: 'rgba(255,255,255,0.75)',
  },
  statusBar: {
    height: 44,
  },
  navRow: {
    height: 52,
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 16,
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

export default BrandHeader;
