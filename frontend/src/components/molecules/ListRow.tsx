import React, { memo, ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Chip, { ChipProps } from '@components/atoms/Chip';
import Icon from '@components/atoms/Icon';

export type ListRowMetaTone = 'neutral' | 'success' | 'error';

export interface ListRowProps {
  title: string;
  subtitle?: string;
  /** Icon tile, avatar, plain icon… */
  leading?: ReactNode;
  /** A string renders as a bold right-aligned value; pass a node for a Switch, Radio, Chip… */
  trailing?: ReactNode;
  status?: Pick<ChipProps, 'label' | 'tone' | 'icon'>;
  /** Paragraph under the title block, e.g. an SMS body or reminder detail. */
  body?: string;
  /** Last small line, e.g. "Existing expense · Groceries" or a "+1.50 (+1.60%)" price change. */
  meta?: string;
  metaTone?: ListRowMetaTone;
  showChevron?: boolean;
  onPress?: () => void;
}

const META_COLOR: Record<ListRowMetaTone, string> = {
  neutral: colors.text.secondary,
  success: colors.tone.success.foreground,
  error: colors.tone.error.foreground,
};

/**
 * The app's single list/row primitive: settings rows, key–value detail lines,
 * transaction rows, bank-message rows, market quotes, reminders.
 */
const ListRow: React.FC<ListRowProps> = ({
  title,
  subtitle,
  leading,
  trailing,
  status,
  body,
  meta,
  metaTone = 'neutral',
  showChevron = false,
  onPress,
}) => {
  const isMultiline = Boolean(status || body || meta);

  const content = (
    <>
      {leading}
      <View style={styles.copy}>
        <AppText variant="subheading14" numberOfLines={2}>
          {title}
        </AppText>
        {subtitle ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {subtitle}
          </AppText>
        ) : null}
        {status ? <Chip {...status} style={styles.status} /> : null}
        {body ? (
          <AppText variant="body14" color={colors.text.secondary} style={styles.body}>
            {body}
          </AppText>
        ) : null}
        {meta ? (
          <AppText variant="body12" color={META_COLOR[metaTone]}>
            {meta}
          </AppText>
        ) : null}
      </View>
      {typeof trailing === 'string' ? (
        <AppText variant="subheading14" align="right" style={styles.trailingText}>
          {trailing}
        </AppText>
      ) : (
        trailing
      )}
      {showChevron ? <Icon name="chevron-right" size={18} color={colors.text.secondary} /> : null}
    </>
  );

  const rowStyle = [styles.row, isMultiline ? styles.alignTop : styles.alignCenter];

  if (!onPress) {
    return <View style={rowStyle}>{content}</View>;
  }

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole="button"
      style={({ pressed }) => [rowStyle, pressed && styles.pressed]}
    >
      {content}
    </Pressable>
  );
};

const styles = StyleSheet.create({
  row: { width: '100%', flexDirection: 'row', gap: 12, minHeight: 24 },
  alignCenter: { alignItems: 'center' },
  alignTop: { alignItems: 'flex-start' },
  copy: { flex: 1, gap: 3 },
  status: { marginTop: 4 },
  body: { marginTop: 4 },
  trailingText: { maxWidth: '50%' },
  pressed: { opacity: 0.6 },
});

export default memo(ListRow);
