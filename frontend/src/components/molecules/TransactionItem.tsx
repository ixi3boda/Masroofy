import React, { memo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import IconTile from '@components/atoms/IconTile';
import { IconName } from '@components/atoms/Icon';

/** card = standalone elevated row (Home) · plain = row inside a grouped card with dividers. */
export type TransactionItemVariant = 'card' | 'plain';

export interface TransactionItemProps {
  title: string;
  /** e.g. "Groceries • 28 Oct" or "Expense · Groceries · CIB •4821" */
  meta: string;
  /** Pre-formatted, signed amount, e.g. "− EGP 850". */
  amount: string;
  icon: IconName;
  variant?: TransactionItemVariant;
  onPress?: () => void;
}

const TransactionItem: React.FC<TransactionItemProps> = ({
  title,
  meta,
  amount,
  icon,
  variant = 'card',
  onPress,
}) => {
  const row = (
    <>
      <IconTile name={icon} />
      <View style={styles.copy}>
        <AppText variant="subheading14" numberOfLines={1}>
          {title}
        </AppText>
        <AppText variant="body12" color={colors.text.secondary} numberOfLines={2}>
          {meta}
        </AppText>
      </View>
      <AppText variant="subheading14" style={styles.amount}>
        {amount}
      </AppText>
    </>
  );

  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole="button"
      accessibilityLabel={`${title}, ${meta}, ${amount}`}
      style={({ pressed }) => pressed && styles.pressed}
    >
      {variant === 'card' ? (
        <Card style={[styles.row, styles.card]}>{row}</Card>
      ) : (
        <View style={styles.row}>{row}</View>
      )}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  pressed: { opacity: 0.8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  card: { padding: 12, borderRadius: radii.lg },
  copy: { flex: 1, gap: 2 },
  amount: { maxWidth: 170 },
});

export default memo(TransactionItem);
