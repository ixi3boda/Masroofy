import React, { Fragment } from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Divider from '@components/atoms/Divider';

export interface SummaryCardProps {
  heading: string;
  rows: string[];
  /** 'subheading14' for short bold bullets (Welcome), 'body14' for sentence-length copy. */
  rowVariant?: 'subheading14' | 'body14';
  style?: StyleProp<ViewStyle>;
}

const SummaryCard: React.FC<SummaryCardProps> = ({ heading, rows, rowVariant = 'body14', style }) => (
  <Card style={style}>
    <AppText variant="subheading16">{heading}</AppText>
    {rows.map((row, index) => (
      <Fragment key={row}>
        {index > 0 ? <Divider /> : null}
        <AppText variant={rowVariant} color={rowVariant === 'body14' ? colors.text.secondary : undefined}>
          {row}
        </AppText>
      </Fragment>
    ))}
  </Card>
);

export default SummaryCard;
