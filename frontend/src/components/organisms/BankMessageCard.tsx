import React, { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import Chip, { ChipProps } from '@components/atoms/Chip';
import ListRow from '@components/molecules/ListRow';
import { strings } from '@/strings';

export interface BankMessageCardProps {
  bank: string;
  /** e.g. "28 Oct 2026 · 14:32" */
  receivedAt: string;
  /** Pre-formatted, e.g. "EGP 850". */
  amount: string;
  /** The SMS text exactly as imported (read-only). */
  body: string;
  /** Between the text and the actions, e.g. a "Possible duplicate" warning banner. */
  notice?: ReactNode;
  status: Pick<ChipProps, 'label' | 'tone'>;
  /** Link label without the arrow, e.g. "Review message". */
  actionLabel: string;
  onAction: () => void;
}

/** One imported bank SMS in the messages list: sender, time, amount, source text, status and review link. */
const BankMessageCard: React.FC<BankMessageCardProps> = ({
  bank,
  receivedAt,
  amount,
  body,
  notice,
  status,
  actionLabel,
  onAction,
}) => (
  <Card>
    <ListRow title={bank} subtitle={receivedAt} trailing={amount} />
    <AppText variant="body14">{body}</AppText>
    {notice}
    <View style={styles.actions}>
      <Chip {...status} style={styles.status} />
      <Button title={strings.common.linkArrow(actionLabel)} variant="link" size="sm" onPress={onAction} />
    </View>
  </Card>
);

const styles = StyleSheet.create({
  actions: { flexDirection: 'row', alignItems: 'center' },
  // Chip pins itself to the top by default; centre it on the link's line.
  status: { alignSelf: 'center' },
});

export default BankMessageCard;
