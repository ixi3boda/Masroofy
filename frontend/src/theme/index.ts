import { colors } from './colors';
import { typography } from './typography';
import { spacing } from './spacing';
import { radii } from './radii';
import { shadows } from './shadows';
import { gradients } from './gradients';

export { colors } from './colors';
export type { Colors } from './colors';
export { typography } from './typography';
export type { TypographyVariant } from './typography';
export { spacing } from './spacing';
export { radii } from './radii';
export { shadows } from './shadows';
export { gradients } from './gradients';

export const theme = { colors, typography, spacing, radii, shadows, gradients };

export type Theme = typeof theme;
