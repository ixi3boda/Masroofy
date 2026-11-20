import { TextStyle } from 'react-native';

/**
 * Typography tokens — sourced from the Masroofy Figma file
 * ("01 / Welcome, Authentication & Onboarding", Typography page).
 * Font families must match the weights loaded in `src/app/_layout.tsx`
 * (@expo-google-fonts/inter).
 */
export const typography = {
  h1: { fontFamily: 'Inter_600SemiBold', fontWeight: '600', fontSize: 28, lineHeight: 34 },
  h2: { fontFamily: 'Inter_600SemiBold', fontWeight: '600', fontSize: 26, lineHeight: 31 },

  subheading18: {
    fontFamily: 'Inter_600SemiBold',
    fontWeight: '600',
    fontSize: 18,
    lineHeight: 20,
    letterSpacing: 0.36,
  },
  subheading16: { fontFamily: 'Inter_600SemiBold', fontWeight: '600', fontSize: 16, lineHeight: 20 },
  subheading14: { fontFamily: 'Inter_600SemiBold', fontWeight: '600', fontSize: 14, lineHeight: 20 },
  subheading13: { fontFamily: 'Inter_600SemiBold', fontWeight: '600', fontSize: 13, lineHeight: 19 },
  subheading12: {
    fontFamily: 'Inter_600SemiBold',
    fontWeight: '600',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.24,
  },

  label12: { fontFamily: 'Inter_600SemiBold', fontWeight: '600', fontSize: 12, lineHeight: 17 },

  body14: {
    fontFamily: 'Inter_400Regular',
    fontWeight: '400',
    fontSize: 14,
    lineHeight: 20,
    letterSpacing: 0.28,
  },
  body12: {
    fontFamily: 'Inter_400Regular',
    fontWeight: '400',
    fontSize: 12,
    lineHeight: 16,
    letterSpacing: 0.24,
  },
  caption10: { fontFamily: 'Inter_400Regular', fontWeight: '400', fontSize: 10, lineHeight: 12 },
} satisfies Record<string, TextStyle>;

export type TypographyVariant = keyof typeof typography;
