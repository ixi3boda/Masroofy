import React from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import DividedCard from '@components/molecules/DividedCard';

export interface SummaryCardProps {
  heading: string;
  rows: string[];
  /** 'subheading14' for short bold bullets (Welcome), 'body14' for sentence-length copy. */
  rowVariant?: 'subheading14' | 'body14';
  style?: StyleProp<ViewStyle>;
}

/** Text-only DividedCard: a heading over short lines (tips, steps, recovery advice). */
const SummaryCard: React.FC<SummaryCardProps> = ({ heading, rows, rowVariant = 'body14', style }) => (
  <DividedCard title={heading} style={style}>
    {rows.map((row) => (
      <AppText key={row} variant={rowVariant} color={rowVariant === 'body14' ? colors.text.secondary : undefined}>
        {row}
      </AppText>
    ))}
  </DividedCard>
);

export default SummaryCard;
