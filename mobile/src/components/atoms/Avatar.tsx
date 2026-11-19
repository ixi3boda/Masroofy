/**
 * Avatar atom — Masroofy design system
 * Shows profile image if `source` is provided; otherwise renders initials.
 */
import React from 'react';
import {
  Image,
  ImageSourcePropType,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from 'react-native';
import AppText from './Text';

// ─── Types ────────────────────────────────────────────────────────────────────
export interface AvatarProps {
  source?: ImageSourcePropType;
  initials?: string;
  size?: number;
  style?: StyleProp<ViewStyle>;
}

// ─── Component ────────────────────────────────────────────────────────────────
const Avatar: React.FC<AvatarProps> = ({
  source,
  initials = '',
  size = 40,
  style,
}) => {
  const radius = size / 2;

  if (source) {
    return (
      <Image
        source={source}
        style={[
          styles.base,
          { width: size, height: size, borderRadius: radius },
          style as any,
        ]}
        resizeMode="cover"
      />
    );
  }

  // Initials fallback
  const fontSize = size * 0.36;
  return (
    <View
      style={[
        styles.base,
        styles.initialsContainer,
        { width: size, height: size, borderRadius: radius },
        style,
      ]}
    >
      <AppText
        variant="subheading14"
        color="#536171"
        style={{ fontSize, lineHeight: undefined }}
      >
        {initials.toUpperCase()}
      </AppText>
    </View>
  );
};

// ─── Styles ───────────────────────────────────────────────────────────────────
const styles = StyleSheet.create({
  base: {
    overflow: 'hidden',
  } as ViewStyle,
  initialsContainer: {
    backgroundColor: '#EBEEF0',
    alignItems: 'center',
    justifyContent: 'center',
  } as ViewStyle,
});

export default Avatar;
