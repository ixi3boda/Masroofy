import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Divider from '@components/atoms/Divider';

export interface ReceiptPreviewProps {
  merchant: string;
  /** e.g. "Cairo, Egypt · Receipt 4821" */
  subtitle: string;
  date: string;
  time: string;
  /** e.g. "TOTAL · EGP" */
  totalLabel: string;
  total: string;
  /** e.g. "Paid by card •4821 · VAT included" */
  footnote?: string;
}

/** Paper-slip rendering of an attached or scanned receipt. */
const ReceiptPreview: React.FC<ReceiptPreviewProps> = ({
  merchant,
  subtitle,
  date,
  time,
  totalLabel,
  total,
  footnote,
}) => (
  <View style={styles.slip} accessible accessibilityLabel={`Receipt from ${merchant}, ${date} ${time}, total ${total}`}>
    <AppText variant="subheading16" align="center" style={styles.merchant}>
      {merchant}
    </AppText>
    <AppText variant="body12" color={colors.text.secondary} align="center">
      {subtitle}
    </AppText>
    <Divider />
    <View style={styles.row}>
      <AppText variant="subheading14">{date}</AppText>
      <AppText variant="subheading14">{time}</AppText>
    </View>
    <Divider />
    <View style={styles.row}>
      <AppText variant="subheading14">{totalLabel}</AppText>
      <AppText variant="subheading14">{total}</AppText>
    </View>
    {footnote ? (
      <AppText variant="body12" color={colors.text.secondary} align="center">
        {footnote}
      </AppText>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  slip: {
    width: '100%',
    gap: 10,
    padding: 16,
    borderRadius: radii.sm,
    borderWidth: 1,
    borderStyle: 'dashed',
    borderColor: colors.border.default,
    backgroundColor: colors.surface,
  },
  merchant: { textTransform: 'uppercase' },
  row: { flexDirection: 'row', justifyContent: 'space-between', gap: 12 },
});

export default ReceiptPreview;
