import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import ChartBar, { ChartBarTone } from '@components/atoms/ChartBar';

export interface BarChartColumnProps {
  label: string;
  value: string;
  height: number;
  tone?: ChartBarTone;
}

const BarChartColumn: React.FC<BarChartColumnProps> = ({ label, value, height, tone }) => (
  <View style={styles.container} accessible accessibilityLabel={`${label} ${value}`}>
    <ChartBar height={height} tone={tone} />
    <View>
      <AppText variant="body12" color={colors.text.secondary}>
        {label}
      </AppText>
      <AppText variant="body12" color={colors.text.secondary}>
        {value}
      </AppText>
    </View>
  </View>
);

const styles = StyleSheet.create({
  container: { alignItems: 'center', gap: 8 },
});

export default BarChartColumn;
