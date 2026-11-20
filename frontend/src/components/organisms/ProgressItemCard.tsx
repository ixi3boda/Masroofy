import React, { memo } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import IconTile from '@components/atoms/IconTile';
import { IconName } from '@components/atoms/Icon';
import { ProgressBarTone } from '@components/atoms/ProgressBar';
import ListRow from '@components/molecules/ListRow';
import ProgressSummary from '@components/molecules/ProgressSummary';
import { strings } from '@/strings';

export interface ProgressItemCardProps {
  icon: IconName;
  title: string;
  /** e.g. "EGP 3,000 used / 4,000 budget" or "Target 30 Apr 2027". */
  subtitle?: string;
  /** Right of the title, e.g. "75%". */
  headline?: string;
  /** Header line above the bar, e.g. "EGP 3,000" / "25%". */
  summaryLabel?: string;
  summaryValue?: string;
  progress: number;
  tone?: ProgressBarTone;
  caption?: string;
  /** Inline link next to the caption, e.g. "Edit". */
  action?: { label: string; onPress: () => void };
  /** Makes the whole card open a detail screen (savings goals); shows a chevron. */
  onPress?: () => void;
}

/** Icon-led card with a progress bar — category budgets, savings goals, budget previews. */
const ProgressItemCard: React.FC<ProgressItemCardProps> = ({
  icon,
  title,
  subtitle,
  headline,
  summaryLabel,
  summaryValue,
  progress,
  tone,
  caption,
  action,
  onPress,
}) => {
  const card = (
    <Card style={styles.card}>
      <ListRow
        leading={<IconTile name={icon} />}
        title={title}
        subtitle={subtitle}
        trailing={headline}
        showChevron={!!onPress}
      />
      <ProgressSummary label={summaryLabel} value={summaryValue} progress={progress} tone={tone} />
      {caption || action ? (
        <View style={styles.footer}>
          <AppText variant="body12" color={colors.text.secondary} style={styles.caption}>
            {caption}
          </AppText>
          {action ? (
            <Button
              title={strings.common.linkArrow(action.label)}
              variant="link"
              size="sm"
              onPress={action.onPress}
              style={styles.action}
            />
          ) : null}
        </View>
      ) : null}
    </Card>
  );

  if (!onPress) return card;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      accessibilityLabel={title}
      style={({ pressed }) => pressed && styles.pressed}
    >
      {card}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  card: { gap: 12 },
  footer: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  caption: { flex: 1 },
  action: { paddingHorizontal: 0, height: 32 },
  pressed: { opacity: 0.85 },
});

export default memo(ProgressItemCard);
