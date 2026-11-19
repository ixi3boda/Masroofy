import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, ViewStyle } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { gradients, radii } from '@theme/index';

export type IconBadgeSize = 'sm' | 'lg';

// sm = brand symbol (rounded square); lg = feature/state mark (full circle)
const PRESET: Record<IconBadgeSize, { containerSize: number; borderRadius: number }> = {
  sm: { containerSize: 72, borderRadius: radii.xl },
  lg: { containerSize: 96, borderRadius: radii.badge },
};

export interface IconBadgeProps {
  children: ReactNode;
  size?: IconBadgeSize;
  style?: StyleProp<ViewStyle>;
}

const IconBadge: React.FC<IconBadgeProps> = ({ children, size = 'sm', style }) => {
  const { containerSize, borderRadius } = PRESET[size];

  return (
    <LinearGradient
      colors={gradients.icon.colors}
      start={gradients.icon.start}
      end={gradients.icon.end}
      style={[
        styles.base,
        { width: containerSize, height: containerSize, borderRadius },
        style,
      ]}
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
