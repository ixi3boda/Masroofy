import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Chip, { ChipTone } from '@components/atoms/Chip';
import IconTile from '@components/atoms/IconTile';
import { IconName } from '@components/atoms/Icon';

export interface TransactionSummaryCardProps {
  icon: IconName;
  title: string;
  /** e.g. "Groceries · Expense" */
  meta: string;
  /** Pre-formatted, e.g. "EGP 850". */
  amount: string;
  status?: { label: string; tone: ChipTone };
  /** e.g. "Already included in October spending" */
  caption?: string;
}

/** Hero card at the top of the transaction details screen. */
const TransactionSummaryCard: React.FC<TransactionSummaryCardProps> = ({
  icon,
  title,
  meta,
  amount,
  status,
  caption,
}) => (
  <Card style={styles.card}>
    <View style={styles.header}>
      <IconTile name={icon} />
      <View style={styles.copy}>
        <AppText variant="subheading18" numberOfLines={1}>
          {title}
        </AppText>
        <AppText variant="body12" color={colors.text.secondary} numberOfLines={1}>
          {meta}
        </AppText>
      </View>
      {status ? <Chip label={status.label} tone={status.tone} /> : null}
    </View>
    <AppText variant="h1" accessibilityRole="header">
      {amount}
    </AppText>
    {caption ? (
      <AppText variant="body12" color={colors.text.secondary}>
        {caption}
      </AppText>
    ) : null}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 12 },
  header: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, gap: 2 },
});

export default TransactionSummaryCard;
