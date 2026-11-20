import React from 'react';
import { StyleProp, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';

export interface DividerProps {
  style?: StyleProp<ViewStyle>;
}

const Divider: React.FC<DividerProps> = ({ style }) => (
  <View style={[{ height: 1, width: '100%', backgroundColor: colors.border.subtle }, style]} />
);

export default Divider;
