import React from 'react';
import { Platform, Switch as RNSwitch } from 'react-native';
import { colors } from '@theme/index';

export interface SwitchProps {
  value: boolean;
  onValueChange: (next: boolean) => void;
  /** Read by screen readers — the visible row title is a separate element. */
  accessibilityLabel: string;
  disabled?: boolean;
}

/** Native on/off toggle styled with brand colours (settings, reminders, alerts). */
const Switch: React.FC<SwitchProps> = ({ value, onValueChange, accessibilityLabel, disabled = false }) => (
  <RNSwitch
    value={value}
    onValueChange={onValueChange}
    disabled={disabled}
    accessibilityLabel={accessibilityLabel}
    trackColor={{ false: colors.text.disabled, true: colors.primary }}
    thumbColor={colors.surface}
    ios_backgroundColor={colors.text.disabled}
    style={Platform.OS === 'web' ? undefined : { transform: [{ scale: 0.95 }] }}
  />
);

export default Switch;
