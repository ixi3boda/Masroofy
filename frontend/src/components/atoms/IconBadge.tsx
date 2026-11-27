import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients, radii } from '@theme/index';

export type IconBadgeSize = 'sm' | 'lg';
/** brand = gradient (success / neutral states) · error = soft red (failures, empty imports). */
export type IconBadgeTone = 'brand' | 'error';

// sm = brand symbol (rounded square); lg = feature/state mark (full circle)
const PRESET: Record<IconBadgeSize, { containerSize: number; borderRadius: number }> = {
  sm: { containerSize: 72, borderRadius: radii.xl },
  lg: { containerSize: 96, borderRadius: radii.badge },
};

export interface IconBadgeProps {
  children: ReactNode;
  size?: IconBadgeSize;
  tone?: IconBadgeTone;
  style?: StyleProp<ViewStyle>;
}

const IconBadge: React.FC<IconBadgeProps> = ({ children, size = 'sm', tone = 'brand', style }) => {
  const { containerSize, borderRadius } = PRESET[size];
  const shape = [styles.base, { width: containerSize, height: containerSize, borderRadius }, style];

  if (tone === 'error') {
    return <View style={[shape, { backgroundColor: colors.tone.error.background }]}>{children}</View>;
  }

  return (
    <LinearGradient
      colors={gradients.icon.colors}
      start={gradients.icon.start}
      end={gradients.icon.end}
      style={shape}
    >
      {children}
    </LinearGradient>
  );
};

const styles = StyleSheet.create({
  base: {
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default IconBadge;
