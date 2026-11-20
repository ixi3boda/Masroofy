/**
 * Brand gradient — used by the icon badge and highlighted surfaces (diagonal)
 * and the primary button (near-vertical). Same stops, different direction in Figma.
 */
const stops = ['#2FDAFF', '#0E33F3'] as const;

export const gradients = {
  icon: { colors: stops, start: { x: 1, y: 0 }, end: { x: 0, y: 1 } },
  button: { colors: stops, start: { x: 0, y: 0 }, end: { x: 0.15, y: 1 } },
};
