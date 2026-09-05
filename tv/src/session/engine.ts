/**
 * The Heart Session engine. Pure TypeScript, no I/O, fully unit-tested.
 *
 * A seated ten-minute protocol for an older adult:
 *   warm 2:00 · work 3:00 · rest 1:00 · work 3:00 · cool 1:00
 *
 * Zones come from the Tanaka estimate of maximum heart rate (208 - 0.7 x age).
 * The engine adapts in two ways only, both conservative:
 *   - if heart rate stays above the work ceiling for 20 s during work, the
 *     current block ends early and the rest block is extended by 30 s;
 *   - if the heart rate was clearly elevated when rest began (10 bpm or more
 *     above the rest target) and recovery is slow (drop under 10 bpm in the
 *     first minute), the next work block is shortened to 2:00. A heart rate
 *     that never rose has nothing to recover from.
 * It never asks for more. It never uses the words monitor, diagnose, alarm.
 */

export type Phase = 'warm' | 'work' | 'rest' | 'cool' | 'done';

export type Block = {phase: Phase; seconds: number};

export type Zones = {max: number; workFloor: number; workCeiling: number; restTarget: number};

export type Sample = {t: number; bpm: number}; // t = seconds since session start

export type Adaptation = {t: number; kind: 'ended-work-early' | 'extended-rest' | 'shortened-next-work'; note: string};

export type SessionState = {
  age: number;
  zones: Zones;
  plan: Block[];
  index: number;         // current block
  blockElapsed: number;  // seconds into current block
  elapsed: number;       // total seconds
  samples: Sample[];
  adaptations: Adaptation[];
  aboveCeilingFor: number; // consecutive seconds above ceiling during work
  restStartBpm: number | null;
  finished: boolean;
};

export const DEFAULT_PLAN: Block[] = [
  {phase: 'warm', seconds: 120},
  {phase: 'work', seconds: 180},
  {phase: 'rest', seconds: 60},
  {phase: 'work', seconds: 180},
  {phase: 'cool', seconds: 60},
];

export function zonesFor(age: number): Zones {
  const max = Math.round(208 - 0.7 * age);
  return {
    max,
    workFloor: Math.round(max * 0.5),     // light, seated
    workCeiling: Math.round(max * 0.65),  // the top of "moderate" for this protocol
    restTarget: Math.round(max * 0.55),
  };
}

export function start(age: number, plan: Block[] = DEFAULT_PLAN): SessionState {
  return {
    age,
    zones: zonesFor(age),
    plan: plan.map(b => ({...b})),
    index: 0,
    blockElapsed: 0,
    elapsed: 0,
    samples: [],
    adaptations: [],
    aboveCeilingFor: 0,
    restStartBpm: null,
    finished: false,
  };
}

export function current(s: SessionState): Block {
  return s.finished ? {phase: 'done', seconds: 0} : s.plan[s.index];
}

export function remainingInBlock(s: SessionState): number {
  return Math.max(0, current(s).seconds - s.blockElapsed);
}

export function totalPlanned(s: SessionState): number {
  return s.plan.reduce((a, b) => a + b.seconds, 0);
}

function advance(s: SessionState): void {
  s.index += 1;
  s.blockElapsed = 0;
  s.aboveCeilingFor = 0;
  if (s.index >= s.plan.length) {
    s.finished = true;
    return;
  }
  if (s.plan[s.index].phase === 'rest') {
    const last = s.samples[s.samples.length - 1];
    s.restStartBpm = last ? last.bpm : null;
  }
}

/** Advance one second, optionally with a heart-rate sample taken this second. Returns a new state. */
export function tick(prev: SessionState, bpm?: number): SessionState {
  if (prev.finished) {
    return prev;
  }
  const s: SessionState = {...prev, plan: prev.plan.map(b => ({...b})), samples: [...prev.samples], adaptations: [...prev.adaptations]};
  s.elapsed += 1;
  s.blockElapsed += 1;
  if (bpm !== undefined) {
    s.samples.push({t: s.elapsed, bpm});
  }
  const block = s.plan[s.index];

  if (block.phase === 'work' && bpm !== undefined) {
    s.aboveCeilingFor = bpm > s.zones.workCeiling ? s.aboveCeilingFor + 1 : 0;
    if (s.aboveCeilingFor >= 20) {
      s.adaptations.push({t: s.elapsed, kind: 'ended-work-early', note: 'Heart rate stayed above the ceiling for 20 seconds; this set ends now.'});
      const next = s.plan[s.index + 1];
      if (next && next.phase === 'rest') {
        next.seconds += 30;
        s.adaptations.push({t: s.elapsed, kind: 'extended-rest', note: 'Rest extended by 30 seconds.'});
      }
      advance(s);
      return s;
    }
  }

  if (block.phase === 'rest' && s.blockElapsed === 60 && s.restStartBpm !== null && bpm !== undefined) {
    const neededRecovery = s.restStartBpm >= s.zones.restTarget + 10;
    if (neededRecovery && s.restStartBpm - bpm < 10) {
      const nextWork = s.plan.slice(s.index + 1).find(b => b.phase === 'work');
      if (nextWork && nextWork.seconds > 120) {
        nextWork.seconds = 120;
        s.adaptations.push({t: s.elapsed, kind: 'shortened-next-work', note: 'Recovery was slow; the next set is two minutes instead of three.'});
      }
    }
  }

  if (s.blockElapsed >= block.seconds) {
    advance(s);
  }
  return s;
}

export type Summary = {
  minutesActive: number;
  minutesPlanned: number;
  avgWorkBpm: number | null;
  peakBpm: number | null;
  inRangeShare: number | null; // share of work samples inside [floor, ceiling]
  adaptations: number;
};

export function summarize(s: SessionState): Summary {
  // Reconstruct which samples fell in work blocks by replaying elapsed times against the (possibly adapted) plan.
  const bounds: {from: number; to: number}[] = [];
  let t = 0;
  for (const b of s.plan) {
    if (b.phase === 'work') {
      bounds.push({from: t, to: t + b.seconds});
    }
    t += b.seconds;
  }
  const work = s.samples.filter(x => bounds.some(b => x.t > b.from && x.t <= b.to));
  const avg = work.length ? Math.round(work.reduce((a, x) => a + x.bpm, 0) / work.length) : null;
  const peak = s.samples.length ? Math.max(...s.samples.map(x => x.bpm)) : null;
  const inRange = work.length ? work.filter(x => x.bpm >= s.zones.workFloor && x.bpm <= s.zones.workCeiling).length / work.length : null;
  return {
    minutesActive: Math.round((s.elapsed / 60) * 10) / 10,
    minutesPlanned: Math.round((totalPlanned(s) / 60) * 10) / 10,
    avgWorkBpm: avg,
    peakBpm: peak,
    inRangeShare: inRange === null ? null : Math.round(inRange * 100) / 100,
    adaptations: s.adaptations.length,
  };
}
