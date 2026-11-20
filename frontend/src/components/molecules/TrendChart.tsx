import React, { useState } from 'react';
import { LayoutChangeEvent, StyleSheet, View } from 'react-native';
import Svg, { Circle, Line, Polyline } from 'react-native-svg';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';

export interface TrendChartProps {
  /** Series values in time order (at least two). */
  points: number[];
  /** Header labels above the plot, e.g. "40,400 pts" and "October 2026". */
  topLeftLabel?: string;
  topRightLabel?: string;
  /** Evenly spread under the plot, e.g. ["1 Oct", "14 Oct", "28 Oct"]. */
  xLabels?: string[];
  height?: number;
}

const GRID_LINES = 4;
const PAD = 6;

/** Line chart with light horizontal gridlines and an end-point marker (market history). */
const TrendChart: React.FC<TrendChartProps> = ({ points, topLeftLabel, topRightLabel, xLabels, height = 140 }) => {
  const [width, setWidth] = useState(0);
  const onLayout = (event: LayoutChangeEvent) => setWidth(event.nativeEvent.layout.width);

  const min = Math.min(...points);
  const range = Math.max(...points) - min || 1;
  const coords = points.map((value, index) => ({
    x: PAD + (index / Math.max(points.length - 1, 1)) * (width - PAD * 2),
    y: PAD + (1 - (value - min) / range) * (height - PAD * 2),
  }));
  const last = coords[coords.length - 1];

  return (
    <View style={styles.container} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
      {topLeftLabel || topRightLabel ? (
        <View style={styles.labels}>
          <AppText variant="body12" color={colors.text.secondary}>
            {topLeftLabel}
          </AppText>
          <AppText variant="body12" color={colors.text.secondary}>
            {topRightLabel}
          </AppText>
        </View>
      ) : null}
      <View style={{ height }} onLayout={onLayout}>
        {width > 0 ? (
          <Svg width={width} height={height}>
            {Array.from({ length: GRID_LINES }).map((_, index) => {
              const y = (height / GRID_LINES) * (index + 1) - 1;
              return <Line key={index} x1={0} x2={width} y1={y} y2={y} stroke={colors.surfaceMuted} strokeWidth={1} />;
            })}
            <Polyline
              points={coords.map(({ x, y }) => `${x},${y}`).join(' ')}
              stroke={colors.primary}
              strokeWidth={3}
              strokeLinejoin="round"
              strokeLinecap="round"
              fill="none"
            />
            {last ? <Circle cx={last.x} cy={last.y} r={5} fill={colors.primary} /> : null}
          </Svg>
        ) : null}
      </View>
      {xLabels?.length ? (
        <View style={styles.labels}>
          {xLabels.map((label) => (
            <AppText key={label} variant="body12" color={colors.text.secondary}>
              {label}
            </AppText>
          ))}
        </View>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { width: '100%', gap: 8 },
  labels: { flexDirection: 'row', justifyContent: 'space-between' },
});

export default TrendChart;
