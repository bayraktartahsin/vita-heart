import React from 'react';
import Svg, {Circle, Defs, LinearGradient, Path, Rect, Stop} from '@amazon-devices/react-native-svg';
import {color} from '../design/tokens';

/** A resting trace: four beats, the last one drawn brighter. Decorative, and honest about it. */
export function EcgResting({width = 620, height = 120}: {width?: number; height?: number}) {
  const past = 'M0,74 L74,74 L88,74 L96,50 L106,96 L118,30 L130,84 L142,74 L206,74 L220,74 L228,52 L238,94 L250,34 L262,84 L274,74 L338,74 L352,74 L360,54 L370,92 L382,36 L394,82 L406,74 L470,74';
  const now = 'M406,74 L470,74 L484,74 L492,48 L502,98 L514,26 L526,86 L538,74 L620,74';
  return (
    <Svg width={width} height={height} viewBox="0 0 620 120">
      <Path d={past} stroke="rgba(255,111,97,0.22)" strokeWidth={3.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <Path d={now} stroke={color.heart} strokeWidth={3.4} fill="none" strokeLinecap="round" strokeLinejoin="round" />
    </Svg>
  );
}

/**
 * The session trace: the last minutes of heart rate as a smooth line over the
 * gentle range. Points come from the engine's own samples, so what is drawn is
 * what the wrist sent; when there are none the card says so instead of drawing.
 */
export function EcgSession({
  samples, floor, ceiling, width, height,
}: {samples: {t: number; bpm: number}[]; floor: number; ceiling: number; width: number; height: number}) {
  const W = 900, H = 620;
  const lo = floor - 26, hi = ceiling + 26;
  const y = (bpm: number) => H - ((Math.max(lo, Math.min(hi, bpm)) - lo) / (hi - lo)) * H;
  const pts = samples.slice(-90);
  const step = pts.length > 1 ? (W - 40) / (pts.length - 1) : 0;
  const line = pts.map((s, i) => `${i === 0 ? 'M' : 'L'}${(i * step).toFixed(1)},${y(s.bpm).toFixed(1)}`).join(' ');
  const last = pts.length ? {x: (pts.length - 1) * step, y: y(pts[pts.length - 1].bpm)} : null;
  // Vega's SVG runtime wants a concrete size and a viewBox set at mount; both are given here.
  return (
    <Svg width={width} height={height} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <Defs>
        <LinearGradient id="under" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={color.heart} stopOpacity="0.3" />
          <Stop offset="1" stopColor={color.heart} stopOpacity="0" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y={y(ceiling)} width={W} height={Math.max(0, y(floor) - y(ceiling))} fill="rgba(121,201,139,0.09)" />
      {pts.length > 1 ? <Path d={`${line} L${(pts.length - 1) * step},${H} L0,${H} Z`} fill="url(#under)" /> : null}
      {pts.length > 1 ? <Path d={line} stroke={color.heart} strokeWidth={5} fill="none" strokeLinecap="round" strokeLinejoin="round" /> : null}
      {last ? <Circle cx={last.x} cy={last.y} r={11} fill={color.heart} /> : null}
      {last ? <Circle cx={last.x} cy={last.y} r={23} stroke="rgba(255,111,97,0.45)" strokeWidth={3} fill="none" /> : null}
    </Svg>
  );
}
