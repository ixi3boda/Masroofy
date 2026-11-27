import React from 'react';
import { Pressable, StyleProp, StyleSheet, ViewStyle } from 'react-native';
import { radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Icon, { IconName } from '@components/atoms/Icon';

export interface QuickActionTileProps {
  label: string;
  icon: IconName;
  /** Shows a notification dot on the icon (e.g. new SMS to review). */
  hasAlert?: boolean;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

const QuickActionTile: React.FC<QuickActionTileProps> = ({ label, icon, hasAlert = false, onPress, style }) => (
  <Pressable
    onPress={onPress}
    disabled={!onPress}
    accessibilityRole="button"
    accessibilityLabel={label}
    style={({ pressed }) => [pressed && styles.pressed, style]}
  >
    <Card style={styles.card}>
      <Icon name={icon} dot={hasAlert} />
      <AppText variant="body12" align="center" numberOfLines={1}>
        {label}
      </AppText>
    </Card>
  </Pressable>
);

const styles = StyleSheet.create({
  pressed: { opacity: 0.8 },
  card: {
    alignItems: 'center',
    gap: 8,
    padding: 16,
    borderRadius: radii.lg,
  },
});

export default QuickActionTile;
