/**
 * Design tokens for a television watched from three metres by a 72-year-old.
 *
 * Type scale never goes below 32 px. Contrast is at least 7:1 on the dark
 * ground. Focus is a 6 px warm ring plus a 4% scale, so it is visible without
 * relying on colour alone.
 */
export const color = {
  ground: '#0F1216',
  panel: '#1A1F26',
  panelRaised: '#232A33',
  text: '#F4F1EA',
  textDim: '#B8B3A8',
  warm: '#F2A93B',       // focus ring, the one accent
  calm: '#7FB77E',       // done, in range
  attention: '#E4B363',  // due, gentle
  heart: '#E8635A',      // heart rate only
  line: '#2E3640',
};

export const type = {
  hero: 120,
  h1: 72,
  h2: 48,
  body: 36,
  small: 32,
};

export const space = {
  xs: 8, s: 16, m: 24, l: 40, xl: 64, xxl: 96,
};

export const radius = { card: 28, pill: 999 };

export const focus = { ring: 6, scale: 1.04 };
