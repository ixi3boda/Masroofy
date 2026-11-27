import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import ProgressBar, { ProgressBarTone } from '@components/atoms/ProgressBar';

export interface ProgressSummaryProps {
  /** Left of the bar's header line, e.g. "EGP 3,000 used". Omit for a bar-only summary. */
  label?: string;
  /** Right of the header line, e.g. "75%". */
  value?: string;
  /** Fraction complete, 0–1. */
  progress: number;
  tone?: ProgressBarTone;
  caption?: string;
  /** strong = bold header (budgets, goals) · subtle = regular secondary header (Home card). */
  emphasis?: 'strong' | 'subtle';
}

/** Header line + progress bar + caption — shared by budget, goal and overview cards. */
const ProgressSummary: React.FC<ProgressSummaryProps> = ({
  label,
  value,
  progress,
  tone,
  caption,
  emphasis = 'strong',
}) => {
  const strong = emphasis === 'strong';

  return (
    <View style={styles.container}>
      {label || value ? (
        <View style={styles.header}>
          <AppText variant={strong ? 'subheading14' : 'body14'} color={strong ? undefined : colors.text.secondary}>
            {label}
          </AppText>
          <AppText variant={strong ? 'subheading14' : 'body14'}>{value}</AppText>
        </View>
      ) : null}
      <ProgressBar progress={progress} tone={tone} />
      {caption ? (
        <AppText variant="body12" color={colors.text.secondary}>
          {caption}
        </AppText>
      ) : null}
    </View>
  );
};

const styles = StyleSheet.create({
  container: { width: '100%', gap: 8 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: 8 },
});

export default ProgressSummary;
