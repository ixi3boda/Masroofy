import { Platform } from 'react-native';

export const shadows = {
  card: Platform.select({
    ios: { shadowColor: '#1D3A58', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.12, shadowRadius: 32 },
    android: { elevation: 8 },
  }),
  cardSm: Platform.select({
    ios: { shadowColor: '#1D3A58', shadowOffset: { width: 0, height: 4 }, shadowOpacity: 0.1, shadowRadius: 16 },
    android: { elevation: 4 },
  }),
  brand: Platform.select({
    ios: { shadowColor: '#1D41F9', shadowOffset: { width: 0, height: 12 }, shadowOpacity: 1, shadowRadius: 24 },
    android: { elevation: 12 },
  }),
  nav: Platform.select({
    ios: { shadowColor: '#1D3A58', shadowOffset: { width: 0, height: 8 }, shadowOpacity: 0.12, shadowRadius: 64 },
    android: { elevation: 16 },
  }),
};
