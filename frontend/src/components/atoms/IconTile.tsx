import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radii } from '@theme/index';
import Icon, { IconName } from './Icon';

export type IconTileSize = 'sm' | 'lg';
export type IconTileTone = 'neutral' | 'onBrand';

// sm = 16px glyph inside an action chip; lg = category icon in list rows
const PRESET: Record<IconTileSize, { box: number; glyph: number; radius: number }> = {
  sm: { box: 24, glyph: 16, radius: radii.sm },
  lg: { box: 44, glyph: 22, radius: 12 },
};

const TONE: Record<IconTileTone, { background: string; foreground: string }> = {
  neutral: { background: colors.surfaceMuted, foreground: colors.text.primary },
  onBrand: { background: colors.overlay.onBrand, foreground: colors.text.inverse },
};

export interface IconTileProps {
  name: IconName;
  size?: IconTileSize;
  tone?: IconTileTone;
  style?: StyleProp<ViewStyle>;
}

const IconTile: React.FC<IconTileProps> = ({ name, size = 'lg', tone = 'neutral', style }) => {
  const { box, glyph, radius } = PRESET[size];
  const { background, foreground } = TONE[tone];

  return (
    <View
      style={[
        styles.base,
        { width: box, height: box, borderRadius: radius, backgroundColor: background },
        style,
      ]}
    >
      <Icon name={name} size={glyph} color={foreground} />
    </View>
  );
};

const styles = StyleSheet.create({
  base: { alignItems: 'center', justifyContent: 'center' },
});

export default IconTile;
