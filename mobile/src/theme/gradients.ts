import { LinearGradient } from 'expo-linear-gradient';

export const gradients = {
  brand: {
    colors: ['#2FDAFF', '#0E33F3'] as const,
    start: { x: 0.2, y: 0 },
    end: { x: 0.8, y: 1 },
  },
  brandVertical: {
    colors: ['#2FDAFF', '#0E33F3'] as const,
    start: { x: 0, y: 0 },
    end: { x: 0, y: 1 },
  },
};
