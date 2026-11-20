import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';

export interface ShutterButtonProps {
  onPress?: () => void;
  accessibilityLabel?: string;
}

const SIZE = 64;

/** Camera capture button (white ring + disc) for dark capture panels. */
const ShutterButton: React.FC<ShutterButtonProps> = ({ onPress, accessibilityLabel = 'Take photo' }) => (
  <Pressable
    onPress={onPress}
    disabled={!onPress}
    accessibilityRole="button"
    accessibilityLabel={accessibilityLabel}
    style={({ pressed }) => [styles.ring, pressed && styles.pressed]}
  >
    <View style={styles.disc} />
  </Pressable>
);

const styles = StyleSheet.create({
  ring: {
    width: SIZE,
    height: SIZE,
    borderRadius: SIZE / 2,
    borderWidth: 3,
    borderColor: colors.surface,
    alignItems: 'center',
    justifyContent: 'center',
  },
  disc: {
    width: SIZE - 14,
    height: SIZE - 14,
    borderRadius: (SIZE - 14) / 2,
    backgroundColor: colors.surface,
  },
  pressed: { transform: [{ scale: 0.94 }] },
});

export default ShutterButton;
