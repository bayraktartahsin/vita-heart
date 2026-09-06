import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {Board} from '../api/client';
import type {LiveState} from '../live/useLiveEvents';
import {BigButton} from '../components/BigButton';
import {BoxThumb} from '../components/BoxThumb';
import {Card, Eyebrow} from '../components/Card';
import {Chip} from '../components/Chip';
import {EcgResting} from '../components/Ecg';
import {Icon} from '../components/Icon';
import {color, type} from '../design/tokens';

type Props = {
  board: Board | null; error: string | null; live: LiveState;
  onCheckin: () => void; onOpenMeds: () => void; onOpenFamily: () => void;
  onStartSession: (source: 'watch' | 'recorded' | 'synthetic') => void; checkinPending: boolean;
};

const SLOTS = ['morning', 'midday', 'evening', 'night'];

/**
 * The first thing the television shows. Four things only: what is due, how his
 * heart was overnight, one line from the family, and one obvious button.
 */
export function MorningBoard({board, error, live, onCheckin, onOpenMeds, onOpenFamily, onStartSession, checkinPending}: Props) {
  if (error) {
    return (
      <View style={styles.centre} testID="board-error">
        <Text style={styles.h2}>The television cannot reach Vita Heart right now.</Text>
        <Text style={styles.p}>{error}</Text>
      </View>
    );
  }
  if (!board) {
    return <View style={styles.centre} testID="board-loading"><Text style={styles.h2}>One moment…</Text></View>;
  }

  const open = board.dueDoses.filter(d => !d.confirmed);
  const next = open[0];
  const recalls = open.reduce((n, d) => n + (d.recallCount || 0), 0);
  const activeSlot = next ? next.slot : 'morning';

  return (
    <View style={styles.grid} testID="morning-board">
      <Card tint="warm" style={styles.hero} testID="card-today">
        <View>
          <Eyebrow icon="clock">This morning</Eyebrow>
          <Text style={styles.h2}>
            {open.length === 0
              ? board.dueDoses.length ? 'Everything taken' : 'Nothing due right now'
              : open.length === 1 ? 'One tablet, with breakfast' : `${open.length} tablets, with breakfast`}
          </Text>
          <Text style={styles.p}>
            {open.length === 0
              ? 'Medication reminders appear here once the boxes are photographed.'
              : 'Due now. The box was photographed from the family\'s phone.'}
          </Text>
        </View>

        {next ? (
          <View style={styles.dose}>
            <BoxThumb name={next.name || 'Unreadable'} strength={next.strength} />
            <View style={styles.doseText}>
              <Text style={styles.doseName} numberOfLines={1}>{next.name || 'Unreadable box'}</Text>
              <Text style={styles.doseMeta}>{next.strength ? `${next.strength} · ` : ''}one tablet{next.food ? ` · ${next.food}` : ''}</Text>
              {next.dueAt ? <Text style={styles.doseWhen}>{next.slot} · {next.dueAt.slice(11, 16)}</Text> : <Text style={styles.doseWhen}>time not set yet</Text>}
            </View>
            <Chip icon="clock" tone="warm">{next.dueAt ? next.dueAt.slice(11, 16) : '—'}</Chip>
          </View>
        ) : null}

        {recalls > 0 ? (
          <View style={styles.safety}>
            <Icon name="shield" size={30} tint={color.warm} />
            <Text style={styles.safetyText}>A batch of this ingredient was recalled. Ask the pharmacist whether your box is affected. Do not stop taking it on your own.</Text>
          </View>
        ) : null}

        <View>
          <View style={styles.band}>
            {SLOTS.map(s => <View key={s} style={[styles.bandSeg, s === activeSlot ? styles.bandNow : null]} />)}
          </View>
          <Text style={styles.bandLabel}>Morning · midday · evening · night</Text>
        </View>

        <View style={styles.actions}>
          {board.checkedInToday ? (
            <Chip icon="check" tone="calm" testID="checked-in">
              {`You said you are up. ${board.family[0]?.name ?? 'The family'} knows.`}
            </Chip>
          ) : (
            <BigButton label={checkinPending ? 'Telling the family…' : "I'm up"} icon="check" onPress={onCheckin} hasTVPreferredFocus disabled={checkinPending} testID="checkin" />
          )}
          {open.length ? <BigButton label="Show me the tablet" icon="pill" tone="quiet" onPress={onOpenMeds} testID="open-meds" /> : null}
        </View>
      </Card>

      <View style={styles.side}>
        <Card tint="heart" testID="card-hr">
          <Eyebrow icon="heart">Resting heart rate</Eyebrow>
          <View style={styles.hrRow}>
            <Text style={styles.hr}>{board.restingHeartRate ?? '—'}</Text>
            <Text style={styles.hrUnit}>beats per minute{'\n'}while he slept</Text>
          </View>
          <View style={styles.ecg}><EcgResting width={560} height={110} /></View>
        </Card>

        <Card style={styles.msgCard} testID="card-message">
          <Eyebrow icon="mail">{board.message ? `From ${board.message.author}` : 'Family'}</Eyebrow>
          <View style={styles.msgRow}>
            {board.message ? <View style={styles.who}><Text style={styles.whoText}>{board.message.author.slice(0, 1)}</Text></View> : null}
            <View style={styles.msgTextWrap}>
              <Text style={styles.msg}>{board.message ? board.message.text : 'No new message.'}</Text>
              {board.message ? <Text style={styles.msgWhen}>{board.message.ts.slice(0, 10)} · {board.message.ts.slice(11, 16)}</Text> : null}
            </View>
          </View>
          <View style={styles.sideActions}>
            <BigButton label="Ten minutes, seated" icon="heart" tone="quiet" compact onPress={() => onStartSession('watch')} testID="start-session" />
            <BigButton label="Family" icon="family" tone="quiet" compact onPress={onOpenFamily} testID="open-family" />
          </View>
        </Card>
      </View>
      <Text style={styles.liveHidden} testID="live-state">{live}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  grid: {flex: 1, flexDirection: 'row', gap: 26},
  hero: {flex: 1.18, gap: 22},
  side: {flex: 0.82, gap: 26},
  centre: {flex: 1, justifyContent: 'center', gap: 20},
  h2: {fontFamily: 'serif', fontSize: type.h2, lineHeight: 56, color: color.text, marginTop: 14, letterSpacing: -0.5},
  p: {fontSize: type.body, lineHeight: 41, color: color.dim, marginTop: 10},
  dose: {flexDirection: 'row', alignItems: 'center', gap: 30, padding: 24, borderRadius: 30,
    backgroundColor: 'rgba(0,0,0,0.32)', borderWidth: 1, borderColor: color.hair},
  doseText: {flex: 1},
  doseName: {fontSize: 38, fontWeight: '600', color: color.text, letterSpacing: -0.3},
  doseMeta: {fontSize: type.small, color: color.dim, marginTop: 4},
  doseWhen: {fontSize: type.small, color: color.warm2, marginTop: 10},
  safety: {flexDirection: 'row', gap: 16, alignItems: 'flex-start', paddingVertical: 20, paddingHorizontal: 24,
    borderRadius: 22, backgroundColor: color.warmSoft, borderWidth: 1, borderColor: color.warmEdge},
  safetyText: {flex: 1, fontSize: type.small, lineHeight: 33, color: color.warmText},
  band: {flexDirection: 'row', gap: 12},
  bandSeg: {flex: 1, height: 10, borderRadius: 6, backgroundColor: color.panel2},
  bandNow: {backgroundColor: color.warm},
  bandLabel: {fontSize: 23, color: color.dim, marginTop: 12},
  actions: {flexDirection: 'row', gap: 22, marginTop: 'auto', alignItems: 'center'},
  hrRow: {flexDirection: 'row', alignItems: 'flex-end', justifyContent: 'space-between'},
  hr: {fontFamily: 'serif', fontSize: type.display, lineHeight: 132, color: color.heart, letterSpacing: -5},
  hrUnit: {fontSize: type.small, lineHeight: 33, color: color.dim, textAlign: 'right'},
  ecg: {marginTop: 'auto', marginBottom: -8},
  msgCard: {flex: 1},
  msgRow: {flexDirection: 'row', alignItems: 'flex-start', gap: 22, marginTop: 6},
  msgTextWrap: {flex: 1},
  who: {width: 60, height: 60, borderRadius: 30, backgroundColor: color.sky, alignItems: 'center', justifyContent: 'center'},
  whoText: {fontSize: 25, fontWeight: '700', color: '#06131F'},
  msg: {fontFamily: 'serif', fontSize: 37, lineHeight: 47, color: color.text},
  msgWhen: {fontSize: 23, color: color.dim, marginTop: 12},
  sideActions: {flexDirection: 'row', gap: 16, marginTop: 'auto'},
  liveHidden: {position: 'absolute', opacity: 0, fontSize: 1},
});
