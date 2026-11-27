import React from 'react';
import { StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients } from '@theme/index';
import AppText from './Text';

export interface AvatarProps {
  /** Full name; the first letters of the first two words are shown. */
  name: string;
  size?: number;
}

const initialsOf = (name: string) =>
  name
    .trim()
    .split(/\s+/)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? '')
    .join('');

const Avatar: React.FC<AvatarProps> = ({ name, size = 48 }) => (
  <LinearGradient
    colors={gradients.icon.colors}
    start={gradients.icon.start}
    end={gradients.icon.end}
    style={[styles.base, { width: size, height: size, borderRadius: size / 2 }]}
    accessibilityLabel={name}
  >
    <AppText variant="subheading16" color={colors.text.inverse}>
      {initialsOf(name)}
    </AppText>
  </LinearGradient>
);

const styles = StyleSheet.create({
  base: { alignItems: 'center', justifyContent: 'center' },
});

export default Avatar;
