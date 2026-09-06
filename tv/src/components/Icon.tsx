import React from 'react';
import Svg, {Path} from '@amazon-devices/react-native-svg';
import {color} from '../design/tokens';

/**
 * One stroked icon set for the whole product. No emoji: emoji render differently
 * on every panel and read as clip-art at three metres.
 */
export const PATHS = {
  home: 'M3 10.5 12 3l9 7.5M5.5 9.5V20h13V9.5',
  pill: 'M14.1 3.6 3.6 14.1a4.6 4.6 0 0 0 6.5 6.5L20.6 10.1a4.6 4.6 0 1 0-6.5-6.5ZM8.8 8.8l6.5 6.5',
  heart: 'M20.4 5.6a5 5 0 0 0-7.1 0L12 6.9l-1.3-1.3a5 5 0 1 0-7.1 7.1L12 21l8.4-8.3a5 5 0 0 0 0-7.1Z',
  family: 'M9 11.2a3.6 3.6 0 1 0 0-7.2 3.6 3.6 0 0 0 0 7.2Zm8.4-.4a2.9 2.9 0 1 0 0-5.8 2.9 2.9 0 0 0 0 5.8ZM2.6 20.2c0-3.4 2.9-5.6 6.4-5.6s6.4 2.2 6.4 5.6M17.2 14.4c2.7.4 4.4 2.3 4.4 5',
  clock: 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 7v5.2l3.4 2',
  mail: 'M3.5 6.5h17v11h-17zM3.5 7l8.5 6 8.5-6',
  check: 'M4.5 12.5 9.5 17.5 19.5 6.5',
  arrow: 'M4 12h15M13 6l6 6-6 6',
  spark: 'M13 2.5 4.5 13.8h6.2L10 21.5l8.6-11.4h-6.3z',
  shield: 'M12 2.8 20 6v6c0 4.4-3.3 7.8-8 9.2C7.3 19.8 4 16.4 4 12V6z',
  door: 'M6 3.5h9.5v17H6zM15.5 12h3M12.5 12.4v.2',
  thermo: 'M14 14.2V5.5a2 2 0 1 0-4 0v8.7a4.5 4.5 0 1 0 4 0Z',
  camera: 'M4 8.5h3.2l1.6-2.3h6.4l1.6 2.3H20v11H4zM12 17a3.4 3.4 0 1 0 0-6.8 3.4 3.4 0 0 0 0 6.8Z',
  moon: 'M20 14.5A8.5 8.5 0 0 1 9.5 4 8.5 8.5 0 1 0 20 14.5Z',
  beat: 'M2 12h4l2-5 3 10 3-8 2 3h6',
  mic: 'M12 3.5a3 3 0 0 1 3 3v5a3 3 0 0 1-6 0v-5a3 3 0 0 1 3-3ZM5.5 11a6.5 6.5 0 0 0 13 0M12 17.5V21',
} as const;

export type IconName = keyof typeof PATHS;

export function Icon({name, size = 26, tint = color.dim, width = 2.1}: {name: IconName; size?: number; tint?: string; width?: number}) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">
      <Path d={PATHS[name]} stroke={tint} strokeWidth={width} strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}
