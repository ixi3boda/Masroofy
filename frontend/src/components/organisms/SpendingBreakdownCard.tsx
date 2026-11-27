import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import DonutChart from '@components/molecules/DonutChart';
import LegendItem from '@components/molecules/LegendItem';

export interface SpendingSlice {
  label: string;
  value: number;
  /** Pre-formatted, e.g. "EGP 5,000". */
  formattedValue: string;
  /** e.g. "40.2% of spending" */
  share: string;
}

export interface SpendingBreakdownCardProps {
  title: string;
  slices: SpendingSlice[];
  centerLabel?: string;
  centerValue?: string;
  centerCaption?: string;
}

/** Donut + legend of where money went; slice colours follow `colors.chart.series` order. */
const SpendingBreakdownCard: React.FC<SpendingBreakdownCardProps> = ({
  title,
  slices,
  centerLabel,
  centerValue,
  centerCaption,
}) => {
  const palette = colors.chart.series;
  const colorAt = (index: number) => palette[index % palette.length];

  return (
    <Card style={styles.card}>
      <AppText variant="subheading16">{title}</AppText>
      <DonutChart
        segments={slices.map((slice, index) => ({ value: slice.value, color: colorAt(index) }))}
        centerLabel={centerLabel}
        centerValue={centerValue}
        centerCaption={centerCaption}
      />
      <View style={styles.legend}>
        {slices.map((slice, index) => (
          <LegendItem
            key={slice.label}
            color={colorAt(index)}
            label={slice.label}
            value={slice.formattedValue}
            caption={slice.share}
          />
        ))}
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { gap: 20 },
  legend: { gap: 14 },
});

export default SpendingBreakdownCard;
