import React, {useEffect, useRef, useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {BigButton} from '../components/BigButton';
import {Card, Eyebrow} from '../components/Card';
import {EcgSession} from '../components/Ecg';
import {Icon} from '../components/Icon';
import {color, type} from '../design/tokens';
import {SessionState, current, remainingInBlock, summarize, tick} from '../session/engine';

export type SessionSource = 'watch' | 'recorded' | 'synthetic';

type Props = {
  state: SessionState; onTick: (s: SessionState) => void; latestBpm: number | null;
  source: SessionSource; coachLine: string; onFinish: (s: SessionState) => void; onStop: () => void;
};

const PHASE: Record<string, string> = {warm: 'Warm up', work: 'Move gently', rest: 'Rest', cool: 'Cool down', done: 'Done'};
const SOURCE: Record<SessionSource, string> = {
  watch: 'live from your Apple Watch', recorded: 'a recorded session', synthetic: 'a test signal',
};

const mmss = (s: number) => `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`;

/**
 * Ten minutes, seated. The number on the screen is the wrist's latest sample and
 * the line is the samples themselves; the source is written under it every second
 * so a recording is never mistaken for a living heart.
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
      onTick(next);
      if (next.finished && !finished) {
        setFinished(true);
        onFinish(next);
      }
    }, 1000);
    return () => clearInterval(id);
  }, [onTick, onFinish, finished]);

  const z = state.zones;

  if (state.finished) {
    const sum = summarize(state);
    return (
      <View style={styles.doneWrap} testID="session-done">
        <Text style={styles.doneH}>Well done. {sum.minutesActive} minutes.</Text>
        <Text style={styles.doneP}>
          {sum.avgWorkBpm ? `Your heart rate averaged ${sum.avgWorkBpm} while you moved` : 'No heart rate reached the television'}
          {sum.inRangeShare !== null ? `, inside the gentle range ${Math.round(sum.inRangeShare * 100)}% of the time.` : '.'}
        </Text>
        {state.adaptations.length ? <Text style={styles.doneP}>{state.adaptations.map(a => a.note).join(' ')}</Text> : null}
        <BigButton label="Back to the morning board" icon="home" onPress={onStop} hasTVPreferredFocus testID="done-back" />
      </View>
    );
  }

  const block = current(state);
  const inZone = latestBpm !== null && latestBpm >= z.workFloor && latestBpm <= z.workCeiling;
  const planned = state.plan.reduce((a, b) => a + b.seconds, 0);

  return (
    <View style={styles.wrap} testID="heart-session">
      <View style={styles.stage}>
        <Card tint="heart" style={styles.now}>
          <Eyebrow icon="heart">Right now</Eyebrow>
          <Text style={styles.bpm} testID="bpm">{latestBpm ?? '—'}</Text>
          <Text style={styles.unit}>BEATS PER MINUTE</Text>
          <View style={[styles.src, latestBpm === null ? styles.srcWaiting : null]}>
            <View style={styles.srcDot} />
            <Text style={styles.srcText}>{latestBpm === null ? 'waiting for the wrist' : SOURCE[source]}</Text>
          </View>
          <View style={styles.zone}>
            <View style={styles.zoneBar}>
              <View style={styles.zoneIn} />
              {latestBpm !== null ? (
                <View style={[styles.zoneMe, {left: `${Math.max(0, Math.min(96, ((latestBpm - (z.workFloor - 26)) / ((z.workCeiling + 26) - (z.workFloor - 26))) * 100))}%`}]} />
              ) : null}
            </View>
            <View style={styles.zoneLabels}>
              <Text style={styles.zoneLabel}>easy {z.workFloor}</Text>
              <Text style={[styles.zoneLabel, {color: inZone ? color.calm : color.dim}]}>gentle range</Text>
              <Text style={styles.zoneLabel}>ceiling {z.workCeiling}</Text>
            </View>
          </View>
        </Card>

        <Card style={styles.trace}>
          <View style={styles.traceHead}>
            <View>
              <Eyebrow icon="beat">Gentle range shaded</Eyebrow>
              <Text style={styles.phase} testID="phase">{PHASE[block.phase]}</Text>
            </View>
            <Text style={styles.count} testID="clock">{mmss(remainingInBlock(state))}</Text>
          </View>
          <View style={styles.traceBody}>
            <EcgSession samples={state.samples} floor={z.workFloor} ceiling={z.workCeiling} width={860} height={360} />
          </View>
          <View style={styles.coach}>
            <View style={styles.coachAv}><Icon name="spark" size={26} tint={color.warmInk} width={2.3} /></View>
            <Text style={styles.coachText} testID="coach">{coachLine}</Text>
          </View>
        </Card>
      </View>

      <View style={styles.segs}>
        {state.plan.map((b, i) => {
          const done = i < state.index;
          const now = i === state.index;
          return (
            <View key={i} style={[styles.seg, done ? styles.segDone : null, now ? styles.segNow : null]}>
              {done ? <Icon name="check" size={24} tint={color.calm} /> : null}
              <Text style={[styles.segText, done ? styles.segTextDone : null, now ? styles.segTextNow : null]}>
                {PHASE[b.phase]} {mmss(b.seconds)}
              </Text>
            </View>
          );
        })}
      </View>

      <View style={styles.footer}>
        <BigButton label="Stop" tone="quiet" compact onPress={onStop} hasTVPreferredFocus testID="stop" />
        <Text style={styles.note}>{Math.round(state.elapsed / 60)} of {Math.round(planned / 60)} minutes · the set shortens itself if recovery is slow</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {flex: 1, gap: 22},
  stage: {flex: 1, flexDirection: 'row', gap: 26},
  now: {flex: 0.95, justifyContent: 'center'},
  bpm: {fontFamily: 'serif', fontSize: type.hero, lineHeight: 250, color: color.heart, letterSpacing: -14},
  unit: {fontSize: 30, letterSpacing: 2, color: color.dim, fontWeight: '600', marginTop: 6},
  src: {flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 16, paddingHorizontal: 26, borderRadius: 999,
    backgroundColor: color.heartSoft, borderWidth: 1, borderColor: color.heartEdge, alignSelf: 'flex-start', marginTop: 22},
  srcWaiting: {backgroundColor: color.panel2, borderColor: color.hair},
  srcDot: {width: 12, height: 12, borderRadius: 6, backgroundColor: color.heart},
  srcText: {fontSize: 26, fontWeight: '600', color: color.heart},
  zone: {marginTop: 34},
  zoneBar: {height: 22, borderRadius: 12, backgroundColor: color.panel2, overflow: 'visible'},
  zoneIn: {position: 'absolute', left: '34%', width: '32%', top: 0, bottom: 0, backgroundColor: 'rgba(121,201,139,0.6)', borderRadius: 12},
  zoneMe: {position: 'absolute', top: -9, width: 6, height: 40, borderRadius: 6, backgroundColor: '#FFFFFF'},
  zoneLabels: {flexDirection: 'row', justifyContent: 'space-between', marginTop: 14},
  zoneLabel: {fontSize: 23, color: color.dim},
  trace: {flex: 1.05, paddingVertical: 30, paddingHorizontal: 34},
  traceHead: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'},
  phase: {fontFamily: 'serif', fontSize: 46, lineHeight: 54, color: color.text, marginTop: 10},
  count: {fontFamily: 'serif', fontSize: 60, lineHeight: 66, color: color.text, letterSpacing: -2},
  traceBody: {flex: 1, marginHorizontal: -34, justifyContent: 'center'},
  coach: {flexDirection: 'row', alignItems: 'center', gap: 20, paddingVertical: 22, paddingHorizontal: 28, borderRadius: 28,
    backgroundColor: 'rgba(10,13,18,0.82)', borderWidth: 1, borderColor: color.hair},
  coachAv: {width: 52, height: 52, borderRadius: 16, backgroundColor: color.warm, alignItems: 'center', justifyContent: 'center'},
  coachText: {flex: 1, fontFamily: 'serif', fontSize: type.body, lineHeight: 39, color: color.text},
  segs: {flexDirection: 'row', gap: 10},
  seg: {flex: 1, height: 58, borderRadius: 16, backgroundColor: color.panel, borderWidth: 1, borderColor: color.hair,
    flexDirection: 'row', alignItems: 'center', justifyContent: 'center', gap: 12},
  segDone: {backgroundColor: color.calmSoft, borderColor: color.calmEdge},
  segNow: {backgroundColor: color.warm, borderColor: 'transparent'},
  segText: {fontSize: 23, fontWeight: '600', color: color.dim2},
  segTextDone: {color: color.calm},
  segTextNow: {color: color.warmInk, fontWeight: '700'},
  footer: {flexDirection: 'row', alignItems: 'center', gap: 22},
  note: {fontSize: 23, color: color.dim2},
  doneWrap: {flex: 1, justifyContent: 'center', gap: 24},
  doneH: {fontFamily: 'serif', fontSize: type.h1, lineHeight: 90, color: color.text},
  doneP: {fontSize: type.body, lineHeight: 41, color: color.dim, maxWidth: 1200},
});
