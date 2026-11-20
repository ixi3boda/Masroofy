import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import IconTile from '@components/atoms/IconTile';
import Radio from '@components/atoms/Radio';
import { IconName } from '@components/atoms/Icon';

export interface OptionCardProps {
  title: string;
  description?: string;
  /** Leading category icon (category picker); omitted for plain filters. */
  icon?: IconName;
  selected: boolean;
  onPress: () => void;
}

/** One choice in a single-select list, e.g. a category or an account filter. */
const OptionCard: React.FC<OptionCardProps> = ({ title, description, icon, selected, onPress }) => (
  <Pressable
    onPress={onPress}
    accessibilityRole="radio"
    accessibilityState={{ selected }}
    accessibilityLabel={title}
    style={({ pressed }) => [
      styles.card,
      selected ? styles.selected : styles.idle,
      icon ? styles.withIcon : styles.plain,
      pressed && styles.pressed,
    ]}
  >
    {icon ? <IconTile name={icon} /> : null}
    <View style={styles.copy}>
      <AppText variant="subheading14" numberOfLines={1}>
        {title}
      </AppText>
      {description ? (
        <AppText variant="body12" color={selected ? colors.primary : colors.text.secondary}>
          {description}
        </AppText>
      ) : null}
    </View>
    <Radio selected={selected} />
  </Pressable>
);

const styles = StyleSheet.create({
  card: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 12,
    borderRadius: radii.lg,
    backgroundColor: colors.surface,
  },
  idle: { borderWidth: 1, borderColor: colors.border.default },
  selected: { borderWidth: 2, borderColor: colors.primary },
  withIcon: { minHeight: 68, paddingVertical: 10 },
  plain: { minHeight: 56, paddingVertical: 12 },
  copy: { flex: 1, gap: 2 },
  pressed: { opacity: 0.8 },
});

export default OptionCard;
