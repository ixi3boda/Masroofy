import React from 'react';
import { Pressable, StyleProp, StyleSheet, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients, shadows } from '@theme/index';
import Icon, { IconName } from './Icon';

export interface FabProps {
  accessibilityLabel: string;
  icon?: IconName;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

const SIZE = 64;

const Fab: React.FC<FabProps> = ({ accessibilityLabel, icon = 'plus', onPress, style }) => (
  <Pressable
    onPress={onPress}
    disabled={!onPress}
    accessibilityRole="button"
    accessibilityLabel={accessibilityLabel}
    style={({ pressed }) => [styles.shadow, pressed && styles.pressed, style]}
  >
    <LinearGradient
      colors={gradients.icon.colors}
      start={gradients.icon.start}
      end={gradients.icon.end}
      style={styles.circle}
    >
      <Icon name={icon} size={32} color={colors.text.inverse} />
    </LinearGradient>
  </Pressable>
);

const styles = StyleSheet.create({
  shadow: { borderRadius: SIZE / 2, ...shadows.brand },
  circle: {
    width: SIZE,
    height: SIZE,
    borderRadius: SIZE / 2,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: { transform: [{ scale: 0.95 }] },
});

export default Fab;
