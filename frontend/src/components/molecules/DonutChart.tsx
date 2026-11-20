import React from 'react';
import { StyleSheet, View } from 'react-native';
import Svg, { Circle } from 'react-native-svg';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';

export interface DonutSegment {
  value: number;
  color: string;
}

export interface DonutChartProps {
  segments: DonutSegment[];
  /** Text stacked in the hole, e.g. "October" / "12,450" / "EGP spent". */
  centerLabel?: string;
  centerValue?: string;
  centerCaption?: string;
  size?: number;
  strokeWidth?: number;
}

/** Proportional ring chart; each segment is an arc sized by its share of the total. */
const DonutChart: React.FC<DonutChartProps> = ({
  segments,
  centerLabel,
  centerValue,
  centerCaption,
  size = 180,
  strokeWidth = 28,
}) => {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const total = segments.reduce((sum, segment) => sum + segment.value, 0) || 1;

  const lengths = segments.map((segment) => (segment.value / total) * circumference);
  // Each arc starts where the previous ones end.
  const starts = lengths.map((_, index) => lengths.slice(0, index).reduce((sum, length) => sum + length, 0));

  const arcs = segments.map((segment, index) => {
    const length = lengths[index];
    return (
      <Circle
        key={index}
        cx={size / 2}
        cy={size / 2}
        r={radius}
        stroke={segment.color}
        strokeWidth={strokeWidth}
        strokeDasharray={`${length} ${circumference - length}`}
        strokeDashoffset={-starts[index]}
        fill="none"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
    );
  });

  return (
    <View
      style={[styles.container, { width: size, height: size }]}
      accessible
      accessibilityLabel={[centerLabel, centerValue, centerCaption].filter(Boolean).join(' ')}
    >
      <Svg width={size} height={size}>
        {arcs}
      </Svg>
      <View style={[StyleSheet.absoluteFill, styles.center]}>
        {centerLabel ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {centerLabel}
          </AppText>
        ) : null}
        {centerValue ? <AppText variant="h2">{centerValue}</AppText> : null}
        {centerCaption ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {centerCaption}
          </AppText>
        ) : null}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: { alignSelf: 'center' },
  center: { alignItems: 'center', justifyContent: 'center' },
});

export default DonutChart;
