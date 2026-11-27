import { Platform } from 'react-native';

export const shadows = {
  card: Platform.select({
    ios: {
      shadowColor: '#1D3A58',
      shadowOffset: { width: 0, height: 8 },
      shadowOpacity: 0.12,
      shadowRadius: 64,
    },
    android: { elevation: 8 },
    default: {},
  }),
  brand: Platform.select({
    ios: {
      shadowColor: '#1D41F9',
      shadowOffset: { width: 0, height: 12 },
      shadowOpacity: 0.35,
      shadowRadius: 12,
    },
    android: { elevation: 10, shadowColor: '#1D41F9' },
    default: {},
  }),
};
