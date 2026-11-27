import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import ChartBar from '@components/atoms/ChartBar';
import LegendItem from '@components/molecules/LegendItem';

export interface BarSeries {
  label: string;
  tone: 'primary' | 'accent';
}

export interface BarGroup {
  label: string;
  /** One value per series, in `series` order. */
  values: number[];
}

export interface GroupedBarChartCardProps {
  title: string;
  /** e.g. "EGP 30,000 maximum · Equal scale" */
  subtitle?: string;
  series: BarSeries[];
  groups: BarGroup[];
  height?: number;
}

const TONE_COLOR: Record<BarSeries['tone'], string> = {
  primary: colors.primary,
  accent: colors.chart.accent,
};

/** Side-by-side bars per period on one shared scale (monthly comparison). */
const GroupedBarChartCard: React.FC<GroupedBarChartCardProps> = ({ title, subtitle, series, groups, height = 150 }) => {
  const peak = Math.max(1, ...groups.flatMap((group) => group.values));

  return (
    <Card style={styles.card}>
      <View style={styles.heading}>
        <AppText variant="subheading16">{title}</AppText>
        {subtitle ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {subtitle}
          </AppText>
        ) : null}
      </View>
      <View style={[styles.plot, { height: height + 28 }]}>
        {groups.map((group) => (
          <View
            key={group.label}
            style={styles.group}
            accessible
            accessibilityLabel={`${group.label}: ${group.values.map((value, i) => `${series[i]?.label} ${value}`).join(', ')}`}
          >
            <View style={[styles.bars, { height }]}>
              {group.values.map((value, index) => (
                <ChartBar key={series[index]?.label ?? index} height={(value / peak) * height} tone={series[index]?.tone} width={32} />
              ))}
            </View>
            <AppText variant="body12" color={colors.text.secondary}>
              {group.label}
            </AppText>
          </View>
        ))}
      </View>
      <View style={styles.legend}>
        {series.map((item) => (
          <LegendItem key={item.label} color={TONE_COLOR[item.tone]} label={item.label} />
        ))}
      </View>
    </Card>
  );
};

const styles = StyleSheet.create({
  card: { gap: 16 },
  heading: { gap: 4 },
  plot: { flexDirection: 'row', justifyContent: 'space-around', alignItems: 'flex-end' },
  group: { alignItems: 'center', gap: 8 },
  bars: { flexDirection: 'row', alignItems: 'flex-end', gap: 12 },
  legend: { flexDirection: 'row', gap: 16 },
});

export default GroupedBarChartCard;
