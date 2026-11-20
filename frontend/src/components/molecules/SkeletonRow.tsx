import React from 'react';
import { StyleSheet, View } from 'react-native';
import { radii } from '@theme/index';
import Card from '@components/atoms/Card';
import Skeleton from '@components/atoms/Skeleton';

/** Loading placeholder shaped like a transaction/list row card. */
const SkeletonRow: React.FC = () => (
  <Card style={styles.card}>
    <Skeleton width={44} height={44} radius={12} />
    <View style={styles.lines}>
      <Skeleton width="70%" />
      <Skeleton width="45%" />
    </View>
    <Skeleton width={56} />
  </Card>
);

const styles = StyleSheet.create({
  card: { flexDirection: 'row', alignItems: 'center', gap: 12, padding: 12, borderRadius: radii.lg },
  lines: { flex: 1, gap: 8 },
});

export default SkeletonRow;
