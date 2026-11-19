/**
 * Chip atom — Masroofy design system
 * Unselected: #EBEEF0 bg, #6B7580 text, r100
 * Selected:   brand gradient bg, white text
 */
import React from 'react';
import {
  StyleProp,
  StyleSheet,
  TouchableOpacity,
  ViewStyle,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import AppText from './Text';

export interface ChipProps {
  label: string;
  selected?: boolean;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

const Chip: React.FC<ChipProps> = ({ label, selected = false, onPress, style }) => {
  if (selected) {
    return (
      <TouchableOpacity onPress={onPress} activeOpacity={0.8} style={style}>
        <LinearGradient
          colors={['#2FDAFF', '#0E33F3']}
          start={{ x: 0, y: 0 }}
          end={{ x: 1, y: 1 }}
          style={styles.base}
        >
          <AppText variant="subheading12" color="#FFFFFF">
            {label}
          </AppText>
        </LinearGradient>
      </TouchableOpacity>
    );
  }

  return (
    <TouchableOpacity
      onPress={onPress}
      activeOpacity={0.75}
      style={[styles.base, styles.unselected, style]}
    >
      <AppText variant="subheading12" color="#6B7580">
        {label}
      </AppText>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  base: {
    borderRadius: 100,
    paddingVertical: 6,
    paddingHorizontal: 14,
    alignItems: 'center',
    justifyContent: 'center',
    alignSelf: 'flex-start',
  } as ViewStyle,
  unselected: {
    backgroundColor: '#EBEEF0',
  } as ViewStyle,
});

export default Chip;
