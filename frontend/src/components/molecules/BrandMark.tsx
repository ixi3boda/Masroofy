import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon from '@components/atoms/Icon';
import IconBadge from '@components/atoms/IconBadge';
import { strings } from '@/strings';

export interface BrandMarkProps {
  style?: StyleProp<ViewStyle>;
}

const BrandMark: React.FC<BrandMarkProps> = ({ style }) => (
  <View style={[styles.container, style]}>
    <IconBadge size="sm">
      <Icon name="wallet" size={36} color={colors.text.inverse} />
    </IconBadge>
    <AppText variant="h1">{strings.common.appName}</AppText>
  </View>
);

const styles = StyleSheet.create({
  container: {
    width: '100%',
    alignItems: 'center',
    gap: 16,
    paddingVertical: 16,
  },
});

export default BrandMark;
