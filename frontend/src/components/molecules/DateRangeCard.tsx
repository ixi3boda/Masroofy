import React from 'react';
import { StyleSheet } from 'react-native';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import SelectField from '@components/atoms/SelectField';

export interface DateRangeCardProps {
  /** Pre-formatted dates, e.g. "1 Oct 2026". */
  from: string;
  to: string;
  onPressFrom?: () => void;
  onPressTo?: () => void;
}

const DateRangeCard: React.FC<DateRangeCardProps> = ({ from, to, onPressFrom, onPressTo }) => (
  <Card style={styles.card}>
    <AppText variant="subheading16">Date range</AppText>
    <SelectField label="From" value={from} onPress={onPressFrom} />
    <SelectField label="To" value={to} onPress={onPressTo} />
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 16 },
});

export default DateRangeCard;
