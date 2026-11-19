import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Checkbox from '@components/atoms/Checkbox';

export interface ConsentCheckboxCardProps {
  title: string;
  description: string;
  checked: boolean;
  onToggle: (next: boolean) => void;
  style?: StyleProp<ViewStyle>;
}

const ConsentCheckboxCard: React.FC<ConsentCheckboxCardProps> = ({
  title,
  description,
  checked,
  onToggle,
  style,
}) => (
  <View style={[styles.card, style]}>
    <View style={styles.copy}>
      <AppText variant="subheading14">{title}</AppText>
      <AppText variant="body12" color={colors.text.secondary}>
        {description}
      </AppText>
    </View>
    <Checkbox checked={checked} onToggle={onToggle} />
  </View>
);

const styles = StyleSheet.create({
  card: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    padding: 14,
    borderRadius: radii.lg,
    borderWidth: 1,
    borderColor: colors.border.default,
    backgroundColor: colors.surface,
  },
  copy: { flex: 1, gap: 4 },
});

export default ConsentCheckboxCard;
