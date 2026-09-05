import React, {useEffect, useRef, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {BigButton} from '../components/BigButton';
import {color, space, type} from '../design/tokens';
import {SessionState, current, remainingInBlock, summarize, tick} from '../session/engine';

export type SessionSource = 'watch' | 'recorded' | 'synthetic';

type Props = {
  state: SessionState;
  onTick: (next: SessionState) => void;
  latestBpm: number | null;
  source: SessionSource;
  coachLine: string;
  onFinish: (state: SessionState) => void;
  onStop: () => void;
};

const PHASE_LABEL: Record<string, string> = {warm: 'Warm up', work: 'Move', rest: 'Rest', cool: 'Cool down', done: 'Done'};
const SOURCE_LABEL: Record<SessionSource, string> = {watch: 'live from your Watch', recorded: 'recorded session', synthetic: 'test signal'};

function mmss(sec: number) {
  return `${Math.floor(sec / 60)}:${String(sec % 60).padStart(2, '0')}`;
}

/** The last 60 seconds of heart rate as bars: no chart library, just Views. */
function Trace({samples, zones}: {samples: {t: number; bpm: number}[]; zones: SessionState['zones']}) {
  const last = samples.slice(-60);
  const lo = zones.workFloor - 15;
  const hi = zones.workCeiling + 15;
  return (
    <View style={styles.trace} testID="trace">
      {last.map(s => {
        const h = Math.max(4, Math.min(1, Math.max(0, (s.bpm - lo) / (hi - lo))) * 160);
        const inZone = s.bpm >= zones.workFloor && s.bpm <= zones.workCeiling;
        return <View key={s.t} style={[styles.bar, {height: h, backgroundColor: inZone ? color.heart : color.textDim}]} />;
      })}
    </View>
  );
}

/**
 * Ten minutes, seated. The engine ticks once a second; the number on screen is
 * the wrist's latest sample and the source is always written next to it.
 */
export function HeartSession({state, onTick, latestBpm, source, coachLine, onFinish, onStop}: Props) {
  const bpmRef = useRef<number | null>(latestBpm);
  bpmRef.current = latestBpm;
  const stateRef = useRef(state);
  stateRef.current = state;
  const [finished, setFinished] = useState(false);

  useEffect(() => {
    const id = setInterval(() => {
      const next = tick(stateRef.current, bpmRef.current ?? undefined);
      stateRef.current = next; // ticks accumulate even if a render has not happened yet
      onTick(next);
      if (next.finished && !finished) {
        setFinished(true);
        onFinish(next);
      }
    }, 1000);
    return () => clearInterval(id);
  }, [onTick, onFinish, finished]);

  const block = current(state);
  const z = state.zones;
  const inZone = latestBpm !== null && latestBpm >= z.workFloor && latestBpm <= z.workCeiling;

  if (state.finished) {
    const sum = summarize(state);
    return (
      <View style={styles.root} testID="session-done">
        <Text style={styles.h1}>Well done, {sum.minutesActive} minutes.</Text>
        <Text style={styles.body}>
          {sum.avgWorkBpm ? `Heart rate averaged ${sum.avgWorkBpm} while moving` : 'No heart rate was received'}
          {sum.inRangeShare !== null ? `, in range ${Math.round(sum.inRangeShare * 100)}% of the time.` : '.'}
          {sum.adaptations ? ` The session adjusted itself ${sum.adaptations} time${sum.adaptations > 1 ? 's' : ''}.` : ''}
        </Text>
        <Text style={styles.body}>{state.adaptations.map(a => a.note).join(' ')}</Text>
        <View style={styles.footer}>
          <BigButton label="Back to the morning board" onPress={onStop} hasTVPreferredFocus testID="done-back" />
        </View>
      </View>
    );
  }

  return (
    <View style={styles.root} testID="heart-session">
      <View style={styles.header}>
        <Text style={styles.phase} testID="phase">{PHASE_LABEL[block.phase]}</Text>
        <Text style={styles.clock} testID="clock">{mmss(remainingInBlock(state))}</Text>
      </View>
      <View style={styles.row}>
        <View style={styles.bpmBox}>
          <Text style={[styles.bpm, {color: latestBpm === null ? color.textDim : inZone ? color.heart : color.attention}]} testID="bpm">
            {latestBpm ?? '—'}
          </Text>
          <Text style={styles.small}>{latestBpm === null ? 'waiting for the wrist' : SOURCE_LABEL[source]}</Text>
          <Text style={styles.small}>gentle range {z.workFloor} to {z.workCeiling}</Text>
        </View>
        <Trace samples={state.samples} zones={z} />
      </View>
      <Text style={styles.coach} testID="coach">{coachLine}</Text>
      <View style={styles.footer}>
        <BigButton label="Stop" tone="quiet" onPress={onStop} testID="stop" hasTVPreferredFocus />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, gap: space.l},
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end'},
  phase: {color: color.text, fontSize: type.h1, fontWeight: '700'},
  clock: {color: color.warm, fontSize: type.h1, fontWeight: '700', fontVariant: ['tabular-nums']},
  row: {flexDirection: 'row', gap: space.xl, alignItems: 'flex-end'},
  bpmBox: {gap: space.xs},
  bpm: {fontSize: 200, fontWeight: '700', lineHeight: 210},
  small: {color: color.textDim, fontSize: type.small},
  trace: {flex: 1, height: 170, flexDirection: 'row', alignItems: 'flex-end', gap: 4},
  bar: {flex: 1, borderRadius: 3},
  coach: {color: color.text, fontSize: type.h2, minHeight: type.h2 * 1.4},
  h1: {color: color.text, fontSize: type.h1, fontWeight: '700'},
  body: {color: color.textDim, fontSize: type.body, lineHeight: type.body * 1.4},
  footer: {marginTop: 'auto'},
});
