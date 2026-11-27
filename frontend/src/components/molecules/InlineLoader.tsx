import React from 'react';
import { ActivityIndicator, StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';

export interface InlineLoaderProps {
  label: string;
}

/** Spinner + status line, e.g. "Loading your overview". */
const InlineLoader: React.FC<InlineLoaderProps> = ({ label }) => (
  <View style={styles.row} accessibilityRole="progressbar" accessibilityLabel={label}>
    <ActivityIndicator size="small" color={colors.text.secondary} />
    <AppText variant="subheading14">{label}</AppText>
  </View>
);

const styles = StyleSheet.create({
  row: { flexDirection: 'row', alignItems: 'center', gap: 10 },
});

export default InlineLoader;
