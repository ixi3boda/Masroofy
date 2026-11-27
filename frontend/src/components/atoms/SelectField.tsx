import React from 'react';
import { Pressable, StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors } from '@theme/index';
import AppText from './Text';
import Icon, { IconName } from './Icon';
import { fieldStyles } from './fieldStyles';

export interface SelectFieldProps {
  label?: string;
  /** Current selection; `placeholder` shows when empty. */
  value?: string;
  placeholder?: string;
  /** Opens the picker (category list, account list…) or screen (search). */
  onPress?: () => void;
  /** Trailing glyph; defaults to the picker chevron. */
  icon?: IconName;
  hasError?: boolean;
  style?: StyleProp<ViewStyle>;
}

/**
 * Read-only field that looks like an Input but opens a picker instead of the
 * keyboard — used for category and account choices, and to open Search.
 */
const SelectField: React.FC<SelectFieldProps> = ({
  label,
  value,
  placeholder,
  onPress,
  icon = 'chevron-down',
  hasError = false,
  style,
}) => (
  <View style={[styles.wrapper, style]}>
    {label ? (
      <AppText variant="label12" color={colors.text.secondary} style={fieldStyles.label}>
        {label}
      </AppText>
    ) : null}
    <Pressable
      onPress={onPress}
      disabled={!onPress}
      accessibilityRole="button"
      accessibilityLabel={label ? `${label}, ${value || placeholder || ''}` : value}
      style={({ pressed }) => [
        fieldStyles.box,
        { borderColor: hasError ? colors.tone.error.foreground : colors.border.default },
        pressed && styles.pressed,
      ]}
    >
      <AppText
        variant="body14"
        // A placeholder is guidance, so it wraps on narrow phones instead of being cut.
        numberOfLines={value ? 1 : 2}
        style={[fieldStyles.value, !value && styles.placeholder]}
      >
        {value || placeholder}
      </AppText>
      {onPress ? <Icon name={icon} size={18} color={colors.text.muted} /> : null}
    </Pressable>
  </View>
);

const styles = StyleSheet.create({
  wrapper: { width: '100%' },
  // After `fieldStyles.value`, whose colour would otherwise win over the text's `color` prop.
  placeholder: { color: colors.text.secondary },
  pressed: { backgroundColor: colors.background },
});

export default SelectField;
