/**
 * Color tokens — sourced from the Masroofy Figma file
 * ("01 / Welcome, Authentication & Onboarding", Colors page,
 * and "02 / Home Dashboard").
 */
export const colors = {
  primary: '#0E33F3',
  primaryLight: '#2FDAFF',
  background: '#F5F6F7',
  surface: '#FFFFFF',
  surfaceMuted: '#EBEEF0',
  notification: '#EF4E4E',

  text: {
    primary: '#242D35',
    secondary: '#6B7580',
    muted: '#9BA1A8',
    disabled: '#B0B8BF',
    inverse: '#FFFFFF',
    inverseMuted: 'rgba(255, 255, 255, 0.8)',
    tab: '#536171',
  },

  overlay: {
    onBrand: 'rgba(255, 255, 255, 0.25)',
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
