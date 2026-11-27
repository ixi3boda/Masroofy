import React from 'react';
import { Pressable, StyleProp, StyleSheet, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import Icon, { IconName } from './Icon';

export interface IconButtonProps {
  name: IconName;
  /** Required: icon-only controls have no visible text for screen readers. */
  accessibilityLabel: string;
  onPress?: () => void;
  size?: number;
  color?: string;
  style?: StyleProp<ViewStyle>;
}

const IconButton: React.FC<IconButtonProps> = ({
  name,
  accessibilityLabel,
  onPress,
  size = 28,
  color = colors.text.primary,
  style,
}) => (
  <Pressable
    onPress={onPress}
    disabled={!onPress}
    accessibilityRole="button"
    accessibilityLabel={accessibilityLabel}
    hitSlop={8}
    style={({ pressed }) => [styles.base, pressed && styles.pressed, style]}
  >
    <Icon name={name} size={size} color={color} strokeWidth={1.75} />
  </Pressable>
);

const styles = StyleSheet.create({
  base: { width: 40, height: 40, alignItems: 'center', justifyContent: 'center' },
  pressed: { opacity: 0.6 },
});

export default IconButton;
