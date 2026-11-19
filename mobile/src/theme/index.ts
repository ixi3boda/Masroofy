export { colors } from './colors';
export type { ColorTheme } from './colors';
export { gradients } from './gradients';
export { spacing } from './spacing';
export { radii } from './radii';
export { typography } from './typography';
export { shadows } from './shadows';

import { colors } from './colors';
import { gradients } from './gradients';
import { spacing } from './spacing';
import { radii } from './radii';
import { typography } from './typography';
import { shadows } from './shadows';

export const theme = {
  colors: colors.light,
  gradients,
  spacing,
  radii,
  typography,
  shadows,
};

export type Theme = typeof theme;
