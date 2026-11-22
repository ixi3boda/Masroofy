import React from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Checkbox from '@components/atoms/Checkbox';
import IconTile from '@components/atoms/IconTile';
import Radio from '@components/atoms/Radio';
import { IconName } from '@components/atoms/Icon';

export interface OptionCardProps {
  title: string;
  description?: string;
  /** Leading category icon (category picker); omitted for plain options. */
  icon?: IconName;
  selected: boolean;
  onPress: () => void;
  /**
   * radio = one of a set (highlighted border when chosen)
   * checkbox = independent yes/no, e.g. consent or "I verified the details".
   */
  kind?: 'radio' | 'checkbox';
}

/** Bordered, fully tappable choice row — single-select options and consent checkboxes. */
const OptionCard: React.FC<OptionCardProps> = ({ title, description, icon, selected, onPress, kind = 'radio' }) => {
  const isRadio = kind === 'radio';
  const highlighted = isRadio && selected;

  return (
    <Pressable
      onPress={onPress}
      accessibilityRole={kind}
      // The aria prop, because react-native-web ignores `accessibilityState`.
      aria-checked={selected}
      accessibilityLabel={description ? `${title}, ${description}` : title}
      style={({ pressed }) => [
        styles.card,
        highlighted ? styles.selected : styles.idle,
        icon ? styles.withIcon : styles.plain,
        pressed && styles.pressed,
      ]}
    >
      {icon ? <IconTile name={icon} /> : null}
      <View style={styles.copy}>
        <AppText variant="subheading14">{title}</AppText>
        {description ? (
          <AppText variant="body12" color={highlighted ? colors.primary : colors.text.secondary}>
            {description}
          </AppText>
        ) : null}
      </View>
      {isRadio ? <Radio selected={selected} /> : <Checkbox checked={selected} />}
    </Pressable>
  );
};

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
