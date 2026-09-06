/**
 * Vita Heart design tokens. The twin of docs/design/kit.css, value for value.
 *
 * Read at three metres by a 72-year-old: nothing below 22 px, body text 29 px,
 * one accent colour per card, and a focus treatment that works without colour.
 */
export const color = {
  ink: '#080A0D',
  ink2: '#0E1218',
  panel: 'rgba(255,255,255,0.05)',
  panel2: 'rgba(255,255,255,0.09)',
  hair: 'rgba(255,255,255,0.09)',
  hair2: 'rgba(255,255,255,0.16)',

  text: '#F6F2EA',
  dim: '#9E9A92',
  dim2: '#6F6C66',

  warm: '#F5B14C',
  warm2: '#FFCE84',
  warmInk: '#20160A',
  warmSoft: 'rgba(245,177,76,0.13)',
  warmEdge: 'rgba(245,177,76,0.32)',
  warmText: '#FFD9A1',

  heart: '#FF6F61',
  heartInk: '#2A0D09',
  heartSoft: 'rgba(255,111,97,0.13)',
  heartEdge: 'rgba(255,111,97,0.30)',

  calm: '#79C98B',
  calmInk: '#0B2312',
  calmSoft: 'rgba(121,201,139,0.13)',
  calmEdge: 'rgba(121,201,139,0.30)',

  sky: '#7FC1FF',
  skySoft: 'rgba(127,193,255,0.11)',
  skyEdge: 'rgba(127,193,255,0.22)',
} as const;

/** Fraunces is not on the device; the display face is the system serif, which Vega maps to a real serif. */
export const font = {
  display: 'serif',
  ui: undefined as string | undefined, // system sans
};

export const type = {
  hero: 300,
  display: 132,
  h1: 82,
  h2: 50,
  h3: 38,
  body: 29,
  small: 25,
  label: 22,
  micro: 21,
} as const;

export const space = {xs: 8, s: 14, m: 20, l: 26, xl: 40, xxl: 72} as const;
export const radius = {card: 40, chip: 20, pill: 999, box: 22} as const;
export const focus = {ring: 5, offset: 7, scale: 1.035} as const;
