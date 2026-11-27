import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon, { IconName } from '@components/atoms/Icon';
import { strings } from '@/strings';

/** pending = not met yet (or only the server can tell) · met = satisfied · failed = broken and blocking. */
export type RequirementStatus = 'pending' | 'met' | 'failed';

export interface Requirement {
  key: string;
  label: string;
  status: RequirementStatus;
}

export interface RequirementListProps {
  items: Requirement[];
  style?: StyleProp<ViewStyle>;
}

const LOOK: Record<RequirementStatus, { icon: IconName; color: string }> = {
  pending: { icon: 'circle', color: colors.text.secondary },
  met: { icon: 'circle-check', color: colors.tone.success.foreground },
  failed: { icon: 'circle-alert', color: colors.tone.error.foreground },
};

/** Live checklist of rules a value must follow, e.g. the password requirements. */
const RequirementList: React.FC<RequirementListProps> = ({ items, style }) => (
  <View style={[styles.list, style]}>
    {items.map(({ key, label, status }) => (
      <View
        key={key}
        style={styles.row}
        accessible
        accessibilityLabel={`${label}, ${strings.common.requirementStatus[status]}`}
      >
        <Icon name={LOOK[status].icon} size={16} color={LOOK[status].color} />
        <AppText variant="body12" color={status === 'pending' ? colors.text.secondary : LOOK[status].color}>
          {label}
        </AppText>
      </View>
    ))}
  </View>
);

const styles = StyleSheet.create({
  list: { gap: 6 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 8 },
});

export default RequirementList;
