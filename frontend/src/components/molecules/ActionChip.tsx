import React from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card, { CardVariant } from '@components/atoms/Card';
import IconTile from '@components/atoms/IconTile';
import { IconName } from '@components/atoms/Icon';

export interface ActionChipProps {
  label: string;
  icon: IconName;
  variant?: CardVariant;
  onPress?: () => void;
}

const ActionChip: React.FC<ActionChipProps> = ({ label, icon, variant = 'default', onPress }) => {
  const onBrand = variant === 'brand';

  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole="button"
      accessibilityLabel={label}
      style={({ pressed }) => pressed && styles.pressed}
    >
      <Card variant={variant} style={styles.card}>
        <IconTile name={icon} size="sm" tone={onBrand ? 'onBrand' : 'neutral'} />
        <AppText variant="subheading12" color={onBrand ? colors.text.inverse : colors.text.primary}>
          {label}
        </AppText>
      </Card>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  pressed: { opacity: 0.8 },
  card: {
    width: 'auto',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    padding: 12,
    borderRadius: radii.lg,
  },
});

export default ActionChip;
