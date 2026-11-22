import React from 'react';
import { Pressable, StyleProp, StyleSheet, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card, { CardVariant } from '@components/atoms/Card';
import Icon, { IconName } from '@components/atoms/Icon';

export interface StatCardProps {
  label: string;
  value: string;
  /** Leading icon; when set the card uses the taller "headline stat" layout. */
  icon?: IconName;
  /** Secondary line under the value, e.g. "Cash · EGP 4,000". */
  caption?: string;
  variant?: CardVariant;
  onPress?: () => void;
  style?: StyleProp<ViewStyle>;
}

const StatCard: React.FC<StatCardProps> = ({
  label,
  value,
  icon,
  caption,
  variant = 'default',
  onPress,
  style,
}) => {
  const onBrand = variant === 'brand';
  const primaryColor = onBrand ? colors.text.inverse : colors.text.primary;
  const secondaryColor = onBrand ? colors.text.inverseMuted : colors.text.secondary;

  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole={onPress ? 'button' : 'summary'}
      accessibilityLabel={`${label}, ${value}${caption ? `, ${caption}` : ''}`}
      style={({ pressed }) => [styles.pressable, pressed && styles.pressed, style]}
    >
      <Card variant={variant} style={[styles.card, icon ? styles.headline : styles.compact]}>
        {icon ? <Icon name={icon} color={primaryColor} /> : null}
        <AppText variant="body12" color={icon ? primaryColor : secondaryColor}>
          {label}
        </AppText>
        <AppText variant="subheading18" color={primaryColor} style={icon && styles.headlineValue} numberOfLines={2}>
          {value}
        </AppText>
        {caption ? (
          <AppText variant="body12" color={secondaryColor} numberOfLines={2}>
            {caption}
          </AppText>
        ) : null}
      </Card>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  pressable: { flex: 1 },
  pressed: { opacity: 0.85 },
  card: { flexGrow: 1, gap: 8, borderRadius: 20 },
  headline: { padding: 20 },
  compact: { padding: 16 },
  headlineValue: { marginTop: 24 },
});

export default StatCard;
