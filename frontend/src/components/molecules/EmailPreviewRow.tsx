import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon from '@components/atoms/Icon';

export interface EmailPreviewRowProps {
  email: string;
  caption?: string;
  style?: StyleProp<ViewStyle>;
}

const EmailPreviewRow: React.FC<EmailPreviewRowProps> = ({ email, caption, style }) => (
  <View style={[styles.container, style]}>
    <View style={styles.row}>
      <Icon name="mail" size={24} />
      <AppText variant="subheading16" align="center" style={styles.email}>
        {email}
      </AppText>
    </View>
    {caption ? (
      <AppText variant="body12" color={colors.text.secondary} align="center">
        {caption}
      </AppText>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  container: { width: '100%', alignItems: 'center', gap: 8 },
  row: {
    width: '100%',
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: radii.md,
    borderWidth: 1,
    borderColor: colors.border.subtle,
    backgroundColor: colors.surface,
  },
  email: { flex: 1 },
});

export default EmailPreviewRow;
