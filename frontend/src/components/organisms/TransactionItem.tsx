import React, { memo } from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { radii } from '@theme/index';
import Card from '@components/atoms/Card';
import IconTile from '@components/atoms/IconTile';
import { IconName } from '@components/atoms/Icon';
import ListRow from '@components/molecules/ListRow';

/** card = standalone elevated row (Home) · plain = row inside a grouped card with dividers. */
export type TransactionItemVariant = 'card' | 'plain';

export interface TransactionItemProps {
  title: string;
  /** e.g. "Groceries • 28 Oct" or "Expense · Groceries · CIB •4821" */
  meta?: string;
  /** Pre-formatted, signed amount, e.g. "− EGP 850". */
  amount: string;
  icon: IconName;
  variant?: TransactionItemVariant;
  onPress?: () => void;
}

/** Category icon + title/meta + amount — a ListRow specialised for money entries. */
const TransactionItem: React.FC<TransactionItemProps> = ({
  title,
  meta,
  amount,
  icon,
  variant = 'card',
  onPress,
}) => {
  const row = <ListRow leading={<IconTile name={icon} />} title={title} subtitle={meta} trailing={amount} />;

  if (variant === 'plain') {
    return onPress ? (
      <Pressable
        onPress={onPress}
        accessibilityRole="button"
        style={({ pressed }) => pressed && styles.pressed}
      >
        {row}
      </Pressable>
    ) : (
      row
    );
  }

  return (
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole="button"
      style={({ pressed }) => pressed && styles.pressed}
    >
      <Card style={styles.card}>{row}</Card>
    </Pressable>
  );
};

const styles = StyleSheet.create({
  pressed: { opacity: 0.8 },
  card: { padding: 12, borderRadius: radii.lg },
});

export default memo(TransactionItem);
