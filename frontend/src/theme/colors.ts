/**
 * Color tokens — sourced from the Masroofy Figma file
 * ("01 / Welcome, Authentication & Onboarding", Colors page,
 * "02 / Home Dashboard" through "11 / Shared States").
 */
export const colors = {
  primary: '#0E33F3',
  primaryLight: '#2FDAFF',
  background: '#F5F6F7',
  surface: '#FFFFFF',
  surfaceMuted: '#EBEEF0',
  /** Dark panel behind the camera / receipt capture preview. */
  surfaceInverse: '#242D35',
  danger: '#EF4E4E',

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
    scrim: 'rgba(36, 45, 53, 0.4)',
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
    warning: { background: '#FFF4E0', foreground: '#9A5B00' },
  },

  /** Categorical series, in order, for donut slices and multi-series bars. */
  chart: {
    series: ['#0E33F3', '#3C6CF6', '#2FC1E5', '#8FB0F7', '#B0BDCC', '#DCE1E6'],
    accent: '#2FC1E5',
  },
};

export type Colors = typeof colors;
