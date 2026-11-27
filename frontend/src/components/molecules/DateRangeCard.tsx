import React from 'react';
import { StyleSheet } from 'react-native';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Input from '@components/atoms/Input';
import { strings } from '@/strings';

export interface DateRangeCardProps {
  /** As typed, e.g. "1 Oct 2026". */
  from: string;
  to: string;
  onChangeFrom: (text: string) => void;
  onChangeTo: (text: string) => void;
  fromError?: string;
  toError?: string;
}

const DateRangeCard: React.FC<DateRangeCardProps> = ({ from, to, onChangeFrom, onChangeTo, fromError, toError }) => (
  <Card style={styles.card}>
    <AppText variant="subheading16">{strings.common.dateRange.title}</AppText>
    <Input
      label={strings.common.dateRange.from}
      value={from}
      onChangeText={onChangeFrom}
      hasError={!!fromError}
      errorMessage={fromError}
    />
    <Input
      label={strings.common.dateRange.to}
      value={to}
      onChangeText={onChangeTo}
      hasError={!!toError}
      errorMessage={toError}
    />
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 16 },
});

export default DateRangeCard;
