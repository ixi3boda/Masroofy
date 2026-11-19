/**
 * Icon atom — Masroofy design system
 * Icon        : placeholder wrapper (swap with react-native-vector-icons etc.)
 * SvgIcon     : renders an SVG via Image (image source).
 */
import React from 'react';
import {
  Image,
  ImageSourcePropType,
  ImageStyle,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from 'react-native';
import AppText from './Text';

// ─── Icon ─────────────────────────────────────────────────────────────────────
export interface IconProps {
  /** Icon name — resolved externally (e.g. by an icon library or switch). */
  name: string;
  size?: number;
  color?: string;
  style?: StyleProp<ViewStyle>;
}

/**
 * Generic icon wrapper.
 * Drop your preferred icon library inside `renderIcon`, or swap this
 * component entirely once a library is added to the project.
 */
const Icon: React.FC<IconProps> = ({ name, size = 24, color = '#242D35', style }) => {
  // Fallback: render the icon name as tiny text so layout is visible.
  // Replace this body with your icon library call (e.g. Ionicons, Feather…).
  return (
    <View style={[{ width: size, height: size, alignItems: 'center', justifyContent: 'center' }, style]}>
      <AppText variant="caption10" color={color} style={{ fontSize: size * 0.4 }}>
        {name}
      </AppText>
    </View>
  );
};

// ─── SvgIcon ──────────────────────────────────────────────────────────────────
export interface SvgIconProps {
  /** An SVG asset loaded via require() or { uri: '…' }. */
  source: ImageSourcePropType;
  size?: number;
  style?: StyleProp<ImageStyle>;
}

/**
 * Renders an SVG asset as a square image.
 * Works with Metro's SVG transformer (react-native-svg-transformer)
 * or plain PNG/WebP fallbacks.
 */
export const SvgIcon: React.FC<SvgIconProps> = ({ source, size = 24, style }) => (
  <Image
    source={source}
    style={[{ width: size, height: size }, style]}
    resizeMode="contain"
  />
);

const _styles = StyleSheet.create({});

export default Icon;
