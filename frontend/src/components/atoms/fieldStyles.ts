import { StyleSheet } from 'react-native';
import { colors, radii } from '@theme/index';

/** Shared look for every form control box (Input, SelectField) so they line up in one form. */
export const fieldStyles = StyleSheet.create({
  label: { marginBottom: 7 },
  box: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderRadius: radii.md,
    height: 48,
    paddingHorizontal: 16,
  },
  value: {
    flex: 1,
    fontFamily: 'Inter_400Regular',
    fontSize: 15,
    letterSpacing: 0.3,
    color: colors.text.primary,
  },
  helper: { marginTop: 4 },
});
