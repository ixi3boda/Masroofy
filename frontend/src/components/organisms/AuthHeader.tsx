import React from 'react';
import { StyleProp, StyleSheet, TouchableOpacity, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon from '@components/atoms/Icon';

export interface AuthHeaderProps {
  title: string;
  onBack?: () => void;
  style?: StyleProp<ViewStyle>;
}

const AuthHeader: React.FC<AuthHeaderProps> = ({ title, onBack, style }) => (
  <View style={[styles.container, style]}>
    {onBack ? (
      <TouchableOpacity onPress={onBack} style={styles.back} hitSlop={8}>
        <Icon name="chevron-left" size={32} />
      </TouchableOpacity>
    ) : null}
    <AppText variant="subheading18" align="center" style={styles.title}>
      {title}
    </AppText>
  </View>
);

const styles = StyleSheet.create({
  container: {
    width: '100%',
    height: 56,
    justifyContent: 'center',
    backgroundColor: colors.surface,
  },
  back: {
    position: 'absolute',
    left: 16,
    top: '50%',
    transform: [{ translateY: -16 }],
  },
  title: {
    marginHorizontal: 56,
  },
});

export default AuthHeader;
