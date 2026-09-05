import {DEFAULT_PLAN, start, summarize, tick, zonesFor} from '../src/session/engine';

const run = (age: number, bpmAt: (t: number) => number, seconds = 700) => {
  let s = start(age);
  for (let t = 1; t <= seconds && !s.finished; t++) {
    s = tick(s, bpmAt(t));
  }
  return s;
};

test('zones follow the Tanaka estimate for a 72-year-old', () => {
  const z = zonesFor(72);
  expect(z.max).toBe(158);
  expect(z.workFloor).toBe(79);
  expect(z.workCeiling).toBe(103);
});

test('a calm session runs the full ten minutes with no adaptation', () => {
  const s = run(72, () => 90);
  expect(s.finished).toBe(true);
  expect(s.elapsed).toBe(600);
  expect(s.adaptations).toEqual([]);
  const sum = summarize(s);
  expect(sum.minutesPlanned).toBe(10);
  expect(sum.avgWorkBpm).toBe(90);
  expect(sum.inRangeShare).toBe(1);
});

test('twenty seconds above the ceiling ends the set early and extends the rest', () => {
  // Warm 120 s at 85, then 110 bpm for the whole first work block.
  const s = run(72, t => (t <= 120 ? 85 : t <= 300 ? 110 : 88));
  const kinds = s.adaptations.map(a => a.kind);
  expect(kinds).toContain('ended-work-early');
  expect(kinds).toContain('extended-rest');
  expect(s.plan[2]).toEqual({phase: 'rest', seconds: 90});
  expect(s.elapsed).toBeLessThan(600);
});

test('a steady low heart rate is not treated as slow recovery', () => {
  const s = run(72, () => 92); // in the work zone but not elevated at rest start: nothing to recover from
  expect(s.adaptations).toEqual([]);
});

test('slow recovery shortens the next work block to two minutes', () => {
  // Rest starts at t=300 with bpm 100 (above the rest target); at t=360 bpm is still 95 (drop < 10).
  const s = run(72, t => (t <= 120 ? 85 : t <= 300 ? 100 : t <= 360 ? 95 : 90));
  expect(s.adaptations.map(a => a.kind)).toContain('shortened-next-work');
  expect(s.plan[3]).toEqual({phase: 'work', seconds: 120});
  expect(s.elapsed).toBe(540);
});

test('tick is pure: the previous state is not mutated', () => {
  const a = start(72);
  const b = tick(a, 80);
  expect(a.elapsed).toBe(0);
  expect(b.elapsed).toBe(1);
  expect(DEFAULT_PLAN[2].seconds).toBe(60);
});

test('ticks after the end are no-ops and summary reports what happened', () => {
  let s = run(72, () => 88);
  const before = s.elapsed;
  s = tick(s, 88);
  expect(s.elapsed).toBe(before);
  expect(summarize(s).minutesActive).toBe(10);
});
