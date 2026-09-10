import React from 'react';
import Svg, {Circle, Defs, LinearGradient, Path, Rect, Stop} from '@amazon-devices/react-native-svg';
import {color, s} from '../design/tokens';

/** A resting trace: four beats, the last one drawn brighter. Decorative, and honest about it. */
export function EcgResting({width = 620, height = 120}: {width?: number; height?: number}) {
  const past = 'M0,74 L74,74 L88,74 L96,50 L106,96 L118,30 L130,84 L142,74 L206,74 L220,74 L228,52 L238,94 L250,34 L262,84 L274,74 L338,74 L352,74 L360,54 L370,92 L382,36 L394,82 L406,74 L470,74';
  const now = 'M406,74 L470,74 L484,74 L492,48 L502,98 L514,26 L526,86 L538,74 L620,74';
  return (
    <Svg width={width} height={height} viewBox="0 0 620 120">
      <Path d={past} stroke="rgba(255,111,97,0.22)" strokeWidth={Math.max(1.5, s(3.4))} fill="none" strokeLinecap="round" strokeLinejoin="round" />
      <Path d={now} stroke={color.heart} strokeWidth={Math.max(1.5, s(3.4))} fill="none" strokeLinecap="round" strokeLinejoin="round" />
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
  // Scale to what is actually on screen. A fixed window around the gentle range left the
  // line pressed into the bottom third of the card with half the height empty, which
  // reads as a flat heart rather than a working one.
  const bpms = samples.length ? samples.slice(-90).map(x => x.bpm) : [];
  let lo = Math.min(floor - 8, ...(bpms.length ? [Math.min(...bpms) - 6] : [floor - 8]));
  let hi = Math.max(ceiling + 8, ...(bpms.length ? [Math.max(...bpms) + 6] : [ceiling + 8]));
  // never less than 44 bpm across the card: a narrow window turns ordinary beat-to-beat
  // variation into alarming spikes, which is a lie told by the axis
  if (hi - lo < 44) { const mid = (hi + lo) / 2; lo = mid - 22; hi = mid + 22; }
  const y = (bpm: number) => H - ((Math.max(lo, Math.min(hi, bpm)) - lo) / (hi - lo)) * H;
  const raw = samples.slice(-90);
  // A reading arrives every few seconds and is then held, so the plain series is a
  // staircase: flat runs and vertical cliffs. That reads as a machine sampling, not as a
  // heart. A short mean over the held values, drawn as a curve, restores what the wrist
  // actually did without inventing a number the summary would disagree with.
  const mean = (a: number[]) => a.reduce((x, y2) => x + y2, 0) / a.length;
  const pts = raw.map((sm, i) => ({
    t: sm.t, bpm: mean(raw.slice(Math.max(0, i - 3), Math.min(raw.length, i + 4)).map(q => q.bpm)),
  }));
  const step = pts.length > 1 ? (W - 40) / (pts.length - 1) : 0;
  const P = pts.map((sm, i) => ({x: i * step, y: y(sm.bpm)}));
  // Catmull-Rom through every point, as cubic sections: no overshoot, no corners.
  const line = P.length < 2 ? '' : P.reduce((d, pt, i) => {
    if (i === 0) { return `M${pt.x.toFixed(1)},${pt.y.toFixed(1)}`; }
    const p0 = P[i - 2] ?? P[i - 1], p1 = P[i - 1], p2 = pt, p3 = P[i + 1] ?? pt;
    const c1x = p1.x + (p2.x - p0.x) / 6, c1y = p1.y + (p2.y - p0.y) / 6;
    const c2x = p2.x - (p3.x - p1.x) / 6, c2y = p2.y - (p3.y - p1.y) / 6;
    return `${d} C${c1x.toFixed(1)},${c1y.toFixed(1)} ${c2x.toFixed(1)},${c2y.toFixed(1)} ${p2.x.toFixed(1)},${p2.y.toFixed(1)}`;
  }, '');
  const last = P.length ? P[P.length - 1] : null;
  // Vega's SVG runtime wants a concrete size and a viewBox set at mount; both are given here.
  return (
    <Svg width={width} height={height} viewBox={`0 0 ${W} ${H}`} preserveAspectRatio="none">
      <Defs>
        <LinearGradient id="under" x1="0" y1="0" x2="0" y2="1">
          <Stop offset="0" stopColor={color.heart} stopOpacity="0.3" />
          <Stop offset="1" stopColor={color.heart} stopOpacity="0" />
        </LinearGradient>
      </Defs>
      <Rect x="0" y={y(ceiling)} width={W} height={Math.max(0, y(floor) - y(ceiling))} fill="rgba(121,201,139,0.055)" />
      <Path d={`M0,${y(ceiling).toFixed(1)} L${W},${y(ceiling).toFixed(1)}`} stroke="rgba(121,201,139,0.30)" strokeWidth={1.5} fill="none" />
      <Path d={`M0,${y(floor).toFixed(1)} L${W},${y(floor).toFixed(1)}`} stroke="rgba(121,201,139,0.30)" strokeWidth={1.5} fill="none" />
      {pts.length > 1 ? <Path d={`${line} L${(pts.length - 1) * step},${H} L0,${H} Z`} fill="url(#under)" /> : null}
      {pts.length > 1 ? <Path d={line} stroke="rgba(255,111,97,0.28)" strokeWidth={Math.max(6, s(16))} fill="none" strokeLinecap="round" strokeLinejoin="round" /> : null}
      {pts.length > 1 ? <Path d={line} stroke={color.heart} strokeWidth={Math.max(2, s(6))} fill="none" strokeLinecap="round" strokeLinejoin="round" /> : null}
      {last ? <Circle cx={last.x} cy={last.y} r={s(11)} fill={color.heart} /> : null}
      {last ? <Circle cx={last.x} cy={last.y} r={s(23)} stroke="rgba(255,111,97,0.45)" strokeWidth={Math.max(1.5, s(3))} fill="none" /> : null}
    </Svg>
  );
}
