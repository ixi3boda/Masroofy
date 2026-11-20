import React, { ReactNode } from 'react';
import { StyleProp, StyleSheet, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Chip, { ChipProps } from '@components/atoms/Chip';

export interface AmountSummaryCardProps {
  /** Row above the amount, e.g. a merchant/account ListRow or a title. */
  header?: ReactNode;
  /** Small uppercase context, e.g. "Total expenses · EGP". */
  overline?: string;
  /** Pre-formatted headline figure, e.g. "EGP 5,600/g" or "12,450". */
  amount: string;
  status?: Pick<ChipProps, 'label' | 'tone' | 'icon'>;
  caption?: string;
  /** Extra rows under the figure: progress, detail rows, actions… */
  children?: ReactNode;
  style?: StyleProp<ViewStyle>;
}

/**
 * Card built around one large figure — balances, totals, quotes, a recorded
 * transaction, a savings target.
 */
const AmountSummaryCard: React.FC<AmountSummaryCardProps> = ({
  header,
  overline,
  amount,
  status,
  caption,
  children,
  style,
}) => (
  <Card style={[styles.card, style]}>
    {header}
    {overline ? (
      <AppText variant="overline12" color={colors.text.secondary}>
        {overline}
      </AppText>
    ) : null}
    <AppText variant="h1" accessibilityRole="header">
      {amount}
    </AppText>
    {status ? <Chip {...status} /> : null}
    {caption ? (
      <AppText variant="body12" color={colors.text.secondary}>
        {caption}
      </AppText>
    ) : null}
    {children}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 10 },
});

export default AmountSummaryCard;
