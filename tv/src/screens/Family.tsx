import React, {useEffect, useState} from 'react';
import {ScrollView, StyleSheet, Text, View} from 'react-native';
import type {Message, Summary, TraceStep, VitaHeartApi} from '../api/client';
import {BigButton} from '../components/BigButton';
import {Card} from '../components/Card';
import {color, space, type} from '../design/tokens';

type Props = {api: VitaHeartApi; onBack: () => void; refreshKey: number};

/**
 * What the family sees, shown to Ahmet too: nothing is said about him behind his back.
 * Tonight's summary, the messages, and the agents' own record of what they looked up.
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
        if (alive) {
          setSummary(s.summary);
          setMessages(m.messages);
          setTrace(t.steps);
          setFailed(false);
        }
      })
      .catch(() => alive && setFailed(true));
    return () => {
      alive = false;
    };
  }, [api, refreshKey]);

  return (
    <View style={styles.root} testID="family">
      <Text style={styles.h1}>Family</Text>
      {failed ? <Text style={styles.body}>The family page could not be loaded right now.</Text> : null}
      <View style={styles.row}>
        <Card title={summary ? `Tonight's summary · ${summary.day}` : 'Tonight'} style={styles.grow} testID="card-summary">
          <Text style={styles.h2}>{summary ? summary.text : 'Night Watch writes one calm paragraph at 21:00.'}</Text>
          {summary?.signals.map(s => (
            <Text key={s.kind + s.note} style={styles.body}>· {s.note}</Text>
          ))}
        </Card>
        <Card title="Messages" style={styles.grow} testID="card-messages">
          {messages.length === 0 ? <Text style={styles.body}>No messages yet.</Text> : null}
          {messages.slice(0, 4).map(m => (
            <Text key={m.ts} style={styles.h2}>
              <Text style={styles.author}>{m.author}: </Text>
              {m.text}
            </Text>
          ))}
        </Card>
      </View>
      <Card title="What the agents looked up" testID="card-trace">
        <ScrollView style={styles.traceBox}>
          {trace.length === 0 ? <Text style={styles.body}>Nothing yet. Photograph the boxes from the phone page.</Text> : null}
          {trace.slice(0, 8).map((t, i) => (
            <Text key={i} style={styles.body}>
              <Text style={styles.author}>{t.agent} · {t.tool}</Text> {t.said ?? ''}
            </Text>
          ))}
        </ScrollView>
      </Card>
      <View style={styles.footer}>
        <BigButton label="Back" tone="quiet" onPress={onBack} hasTVPreferredFocus testID="back" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, gap: space.l},
  h1: {color: color.text, fontSize: type.h1, fontWeight: '700'},
  h2: {color: color.text, fontSize: type.body, lineHeight: type.body * 1.35},
  body: {color: color.textDim, fontSize: type.small, lineHeight: type.small * 1.4},
  author: {color: color.warm},
  row: {flexDirection: 'row', gap: space.l},
  grow: {flex: 1},
  traceBox: {maxHeight: 220},
  footer: {marginTop: 'auto'},
});
