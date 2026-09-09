import {Dimensions} from 'react-native';

/**
 * Vita Heart design tokens. The twin of docs/design/kit.css, value for value.
 *
 * The mockups are drawn at 1920x1080; a Fire TV hands React Native a 960x540
 * logical surface at pixel ratio 2. Every size below is therefore a *design*
 * pixel put through `s()`, which maps the sheet onto whatever the television
 * actually gives. Measured on the device rather than assumed: the first build
 * rendered at twice the size because 1920 was taken for granted.
 *
 * Read at three metres by a 72-year-old: nothing below 22 px, body text 29 px,
 * one accent colour per card, and a focus treatment that works without colour.
 */
const win = Dimensions.get('window');
export const SCALE = Math.min(win.width / 1920, win.height / 1080) || 1;
/** design pixels (1920x1080) → this screen's pixels */
export const s = (n: number) => Math.round(n * SCALE);

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
  hero: s(300),
  display: s(132),
  h1: s(82),
  h2: s(50),
  h3: s(38),
  body: s(29),
  small: s(25),
  label: s(22),
  micro: s(21),
} as const;

export const space = {xs: s(8), s: s(14), m: s(20), l: s(26), xl: s(40), xxl: s(72)} as const;
export const radius = {card: s(40), chip: s(20), pill: 999, box: s(22)} as const;
export const focus = {ring: Math.max(2, s(5)), offset: s(7), scale: 1.035} as const;
