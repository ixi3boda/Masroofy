export const colors = {
  light: {
    primary: '#0E33F3',
    primaryLight: '#2FDAFF',
    background: '#F5F6F7',
    surface: '#FFFFFF',
    text: {
      primary: '#242D35',    // 800
      secondary: '#6B7580',  // 600
      muted: '#9BA1A8',      // 500
      disabled: '#B0B8BF',   // 400
    },
    border: '#EBEEF0',       // 200
    system: {
      error: '#EF4E4E',
      success: '#10B981',
      warning: '#F59E0B',
      info: '#0E33F3',
    },
  },
  dark: {
    primary: '#4D6EFF',
    primaryLight: '#7BDBFF',
    background: '#0F172A',
    surface: '#1E293B',
    text: {
      primary: '#F8FAFC',
      secondary: '#94A3B8',
      muted: '#64748B',
      disabled: '#475569',
    },
    border: '#334155',
    system: {
      error: '#F87171',
      success: '#34D399',
      warning: '#FCD34D',
      info: '#60A5FA',
    },
  },
};

export type ColorTheme = typeof colors.light;
