import React from 'react';
import { StyleSheet } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Input from '@components/atoms/Input';
import FeedbackBanner from './FeedbackBanner';

export interface AmountEntryCardProps {
  /** Small uppercase context line, e.g. "Manual entry · October 2026". */
  overline?: string;
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  /** Shown as an inline error banner under the field. */
  errorMessage?: string;
}

/** Highlighted amount field at the top of add/edit transaction forms. */
const AmountEntryCard: React.FC<AmountEntryCardProps> = ({
  overline,
  label,
  value,
  onChangeText,
  errorMessage,
}) => (
  <Card style={styles.card}>
    {overline ? (
      <AppText variant="overline12" color={colors.text.secondary}>
        {overline}
      </AppText>
    ) : null}
    <Input
      label={label}
      value={value}
      onChangeText={onChangeText}
      keyboardType="decimal-pad"
      hasError={!!errorMessage}
    />
    {errorMessage ? <FeedbackBanner tone="error" icon="circle-alert" title={errorMessage} /> : null}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 12 },
});

export default AmountEntryCard;
