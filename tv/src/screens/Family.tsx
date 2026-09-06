import React, {useEffect, useState} from 'react';
import {ScrollView, StyleSheet, Text, View} from 'react-native';
import type {Message, Summary, TraceStep, VitaHeartApi} from '../api/client';
import {BigButton} from '../components/BigButton';
import {Card, Eyebrow} from '../components/Card';
import {Chip} from '../components/Chip';
import {color, type} from '../design/tokens';

type Props = {api: VitaHeartApi; onBack: () => void; refreshKey: number};

const AGENT_TINT: Record<string, string> = {
  Reader: color.warm2, Identifier: color.warm2, Watchman: color.sky,
  Coach: color.calm, Scribe: color.calm, Scheduler: color.warm2,
};

/**
 * What the family will read, shown to Ahmet first. Nothing is said about him
 * behind his back, and the agents' own record of what they looked up is beside it.
 */
export function Family({api, onBack, refreshKey}: Props) {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [trace, setTrace] = useState<TraceStep[]>([]);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let alive = true;
    Promise.all([api.summary(), api.messages(), api.trace()])
      .then(([s, m, t]) => {
        if (!alive) {
          return;
        }
        setSummary(s.summary);
        setMessages(m.messages);
        setTrace(t.steps);
        setFailed(false);
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [api, refreshKey]);

  const signals = summary?.signals ?? [];
  const latest = messages[0];

  return (
    <View style={styles.wrap} testID="family">
      <View style={styles.left}>
        <Card tint="sky" style={styles.summary} testID="card-summary">
          <Eyebrow icon="moon">Tonight's summary</Eyebrow>
          <Text style={styles.para}>
            {failed ? 'The family page could not be loaded right now.'
              : summary ? summary.text
              : 'Night Watch writes one calm paragraph at 21:00, from the day\'s facts only.'}
          </Text>
          <View style={styles.sig}>
            {signals.slice(0, 5).map(s => (
              <Chip key={s.kind + s.note} tone={s.weight > 1 ? 'warm' : 'calm'} icon={s.weight > 1 ? 'shield' : 'check'}>
                {s.note.length > 46 ? `${s.note.slice(0, 44)}…` : s.note}
              </Chip>
            ))}
          </View>
        </Card>

        <Card style={styles.msgCard} testID="card-messages">
          <Eyebrow icon="mail">Messages</Eyebrow>
          {latest ? (
            <View style={styles.msgRow}>
              <View style={styles.who}><Text style={styles.whoText}>{latest.author.slice(0, 1)}</Text></View>
              <View style={styles.msgTextWrap}>
                <Text style={styles.msg}>{latest.text}</Text>
                <Text style={styles.msgWhen}>{latest.author} · {latest.ts.slice(0, 10)} {latest.ts.slice(11, 16)}</Text>
              </View>
            </View>
          ) : <Text style={styles.p}>No messages yet.</Text>}
        </Card>
      </View>

      <Card style={styles.traceCard} testID="card-trace">
        <Eyebrow icon="spark">What the agents did today</Eyebrow>
        <ScrollView style={styles.traceList}>
          {trace.length === 0 ? <Text style={styles.p}>Nothing yet. Photograph the boxes from the family's phone.</Text> : null}
          {trace.slice(0, 7).map((t, i) => (
            <View key={i} style={[styles.step, i === 0 ? styles.stepFirst : null]}>
              <Text style={[styles.agent, {color: AGENT_TINT[t.agent] ?? color.warm2}]}>{t.agent.toUpperCase()}</Text>
              <Text style={styles.stepText}>{t.said ?? t.tool}</Text>
            </View>
          ))}
        </ScrollView>
        <Chip icon="shield" style={styles.foot}>Nothing is said about Ahmet that he cannot see here</Chip>
      </Card>

      <View style={styles.back}><BigButton label="Back" tone="quiet" compact onPress={onBack} hasTVPreferredFocus testID="back" /></View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {flex: 1, flexDirection: 'row', gap: 26},
  left: {flex: 1.15, gap: 24},
  summary: {flex: 1},
  para: {fontFamily: 'serif', fontSize: 33, lineHeight: 45, color: color.text},
  p: {fontSize: type.small, lineHeight: 34, color: color.dim},
  sig: {flexDirection: 'row', flexWrap: 'wrap', gap: 12, marginTop: 4},
  msgCard: {paddingVertical: 26, paddingHorizontal: 36},
  msgRow: {flexDirection: 'row', gap: 20, alignItems: 'flex-start'},
  msgTextWrap: {flex: 1},
  who: {width: 56, height: 56, borderRadius: 28, backgroundColor: color.sky, alignItems: 'center', justifyContent: 'center'},
  whoText: {fontSize: 24, fontWeight: '700', color: '#06131F'},
  msg: {fontFamily: 'serif', fontSize: 29, lineHeight: 38, color: color.text},
  msgWhen: {fontSize: 22, color: color.dim, marginTop: 8},
  traceCard: {flex: 0.85, paddingVertical: 30, paddingHorizontal: 34},
  traceList: {flex: 1},
  step: {flexDirection: 'row', gap: 18, paddingVertical: 13, borderTopWidth: 1, borderTopColor: color.hair},
  stepFirst: {borderTopWidth: 0, paddingTop: 4},
  agent: {width: 118, fontSize: 18, letterSpacing: 1.6, fontWeight: '700', lineHeight: 23},
  stepText: {flex: 1, fontSize: 23, lineHeight: 31, color: color.dim},
  foot: {marginTop: 14},
  back: {position: 'absolute', left: 0, bottom: -2},
});
