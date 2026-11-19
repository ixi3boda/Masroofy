/**
 * Color tokens — sourced from the Masroofy Figma file
 * ("01 / Welcome, Authentication & Onboarding", Colors page).
 */
export const colors = {
  primary: '#0E33F3',
  primaryLight: '#2FDAFF',
  background: '#F5F6F7',
  surface: '#FFFFFF',

  text: {
    primary: '#242D35',
    secondary: '#6B7580',
    muted: '#9BA1A8',
    disabled: '#B0B8BF',
    inverse: '#FFFFFF',
  },

  border: {
    default: '#DCE1E6',
    subtle: '#EBEEF0',
    otp: '#DCDFE3',
  },

  tone: {
    info: { background: '#EBF0FF', foreground: '#0E33F3' },
    success: { background: '#E8F6F0', foreground: '#167C64' },
    error: { background: '#FFF0F0', foreground: '#BC3434' },
  },
};

export type Colors = typeof colors;
