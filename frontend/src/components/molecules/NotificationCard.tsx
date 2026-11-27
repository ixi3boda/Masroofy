import React, { memo } from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import Chip, { ChipProps } from '@components/atoms/Chip';
import Icon, { IconName } from '@components/atoms/Icon';
import { strings } from '@/strings';

export interface NotificationCardProps {
  status: Pick<ChipProps, 'label' | 'tone'>;
  icon: IconName;
  title: string;
  body: string;
  /** e.g. "28 Oct 2026 · 14:40 · Cairo" */
  timestamp: string;
  action?: { label: string; onPress: () => void };
}

const NotificationCard: React.FC<NotificationCardProps> = ({ status, icon, title, body, timestamp, action }) => (
  <Card style={styles.card}>
    <Chip {...status} />
    <View style={styles.titleRow}>
      <Icon name={icon} size={20} color={colors.tone[status.tone ?? 'info'].foreground} />
      <AppText variant="subheading16" style={styles.title}>
        {title}
      </AppText>
    </View>
    <AppText variant="body14">{body}</AppText>
    <AppText variant="body12" color={colors.text.secondary}>
      {timestamp}
    </AppText>
    {action ? <Button title={strings.common.linkArrow(action.label)} variant="link" size="sm" onPress={action.onPress} style={styles.action} /> : null}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 10 },
  titleRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  title: { flex: 1 },
  action: { paddingHorizontal: 0, height: 32 },
});

export default memo(NotificationCard);
