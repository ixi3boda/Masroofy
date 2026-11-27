import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import Icon from './Icon';

export interface RadioProps {
  selected: boolean;
}

const SIZE = 20;

/**
 * Visual radio indicator only — the surrounding option row owns the press
 * target and the `radio` accessibility role.
 */
const Radio: React.FC<RadioProps> = ({ selected }) => (
  <View style={[styles.base, { borderColor: selected ? colors.primary : colors.text.muted }]}>
    {selected ? <Icon name="check" size={12} color={colors.primary} strokeWidth={3} /> : null}
  </View>
);

const styles = StyleSheet.create({
  base: {
    width: SIZE,
    height: SIZE,
    borderRadius: SIZE / 2,
    borderWidth: 1.5,
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default Radio;
