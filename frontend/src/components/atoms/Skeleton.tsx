import React, { useEffect, useState } from 'react';
import { Animated, DimensionValue, StyleProp, ViewStyle } from 'react-native';
import { colors, radii } from '@theme/index';

export interface SkeletonProps {
  width?: DimensionValue;
  height?: DimensionValue;
  radius?: number;
  style?: StyleProp<ViewStyle>;
}

/** Pulsing placeholder block shown while content loads. */
const Skeleton: React.FC<SkeletonProps> = ({ width = '100%', height = 12, radius = radii.sm, style }) => {
  const [opacity] = useState(() => new Animated.Value(1));

  useEffect(() => {
    const pulse = Animated.loop(
      Animated.sequence([
        Animated.timing(opacity, { toValue: 0.5, duration: 700, useNativeDriver: true }),
        Animated.timing(opacity, { toValue: 1, duration: 700, useNativeDriver: true }),
      ])
    );
    pulse.start();
    return () => pulse.stop();
  }, [opacity]);

  return (
    <Animated.View
      accessibilityElementsHidden
      importantForAccessibility="no-hide-descendants"
      style={[{ width, height, borderRadius: radius, backgroundColor: colors.surfaceMuted, opacity }, style]}
    />
  );
};

export default Skeleton;
