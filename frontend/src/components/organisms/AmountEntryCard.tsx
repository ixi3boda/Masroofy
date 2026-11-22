import React from 'react';
import { StyleSheet } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Input from '@components/atoms/Input';
import FeedbackBanner from '@components/molecules/FeedbackBanner';

export interface AmountEntryCardProps {
  /** Small uppercase context line, e.g. "Manual entry · October 2026". */
  overline?: string;
  label: string;
  value: string;
  onChangeText: (text: string) => void;
  errorMessage?: string;
  /** banner = tinted message under the field (expense) · inline = the field's own helper line (income). */
  errorDisplay?: 'banner' | 'inline';
}

/** Highlighted amount field at the top of add/edit transaction forms. */
const AmountEntryCard: React.FC<AmountEntryCardProps> = ({
  overline,
  label,
  value,
  onChangeText,
  errorMessage,
  errorDisplay = 'banner',
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
      errorMessage={errorDisplay === 'inline' ? errorMessage : undefined}
    />
    {errorMessage && errorDisplay === 'banner' ? (
      <FeedbackBanner tone="error" icon="circle-alert" title={errorMessage} />
    ) : null}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 12 },
});

export default AmountEntryCard;
