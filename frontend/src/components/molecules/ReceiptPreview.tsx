import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Divider from '@components/atoms/Divider';
import { strings } from '@/strings';

export interface ReceiptLineItem {
  label: string;
  amount: string;
}

export interface ReceiptPreviewProps {
  merchant: string;
  /** e.g. "Cairo, Egypt · Receipt 4821" */
  subtitle: string;
  date: string;
  time: string;
  /** Itemised lines between the date and the total (full capture/selection views). */
  items?: ReceiptLineItem[];
  /** e.g. "TOTAL · EGP" */
  totalLabel: string;
  total: string;
  /** e.g. "Paid by card •4821 · VAT included" */
  footnote?: string;
  /** e.g. "Thank you for shopping with us" */
  closingNote?: string;
}

const Line: React.FC<{ left: string; right: string }> = ({ left, right }) => (
  <View style={styles.row}>
    <AppText variant="subheading14">{left}</AppText>
    <AppText variant="subheading14">{right}</AppText>
  </View>
);

/** Paper-slip rendering of an attached, selected or scanned receipt. */
const ReceiptPreview: React.FC<ReceiptPreviewProps> = ({
  merchant,
  subtitle,
  date,
  time,
  items,
  totalLabel,
  total,
  footnote,
  closingNote,
}) => (
  <View
    style={styles.slip}
    accessible
    accessibilityLabel={strings.common.a11y.receipt(merchant, date, time, total)}
  >
    <AppText variant="subheading16" align="center" style={styles.merchant}>
      {merchant}
    </AppText>
    <AppText variant="body12" color={colors.text.secondary} align="center">
      {subtitle}
    </AppText>
    <Divider />
    <Line left={date} right={time} />
    {items?.map((item) => <Line key={item.label} left={item.label} right={item.amount} />)}
    <Divider />
    <Line left={totalLabel} right={total} />
    {footnote ? (
      <AppText variant="body12" color={colors.text.secondary} align="center">
        {footnote}
      </AppText>
    ) : null}
    {closingNote ? (
      <AppText variant="body12" color={colors.text.secondary} align="center">
        {closingNote}
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
