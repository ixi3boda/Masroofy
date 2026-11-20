import React, { memo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import IconTile from '@components/atoms/IconTile';
import { IconName } from '@components/atoms/Icon';

export interface TransactionItemProps {
  title: string;
  /** e.g. "Groceries • 28 Oct" */
  meta: string;
  /** Pre-formatted, signed amount, e.g. "− EGP 850". */
  amount: string;
  icon: IconName;
  onPress?: () => void;
}

const TransactionItem: React.FC<TransactionItemProps> = ({ title, meta, amount, icon, onPress }) => (
  <Pressable
    onPress={onPress}
    disabled={!onPress}
    accessibilityRole="button"
    accessibilityLabel={`${title}, ${meta}, ${amount}`}
    style={({ pressed }) => pressed && styles.pressed}
  >
    <Card style={styles.card}>
      <IconTile name={icon} />
      <View style={styles.copy}>
        <AppText variant="subheading14" numberOfLines={1}>
          {title}
        </AppText>
        <AppText variant="body12" color={colors.text.secondary} numberOfLines={1}>
          {meta}
        </AppText>
      </View>
      <AppText variant="subheading14">{amount}</AppText>
    </Card>
  </Pressable>
);

const styles = StyleSheet.create({
  pressed: { opacity: 0.8 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 12,
    borderRadius: radii.lg,
  },
  copy: { flex: 1, gap: 2 },
});

export default memo(TransactionItem);
