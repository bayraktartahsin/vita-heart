import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {Board} from '../api/client';
import type {LiveState} from '../live/useLiveEvents';
import {BigButton} from '../components/BigButton';
import {Card} from '../components/Card';
import {color, space, type} from '../design/tokens';

type Props = {
  board: Board | null;
  error: string | null;
  live: LiveState;
  onCheckin: () => void;
  checkinPending: boolean;
};

/**
 * The first thing the television shows. Four things only: a greeting, what is
 * due, one line from the family, and one big button. Everything else waits.
 */
export function MorningBoard({board, error, live, onCheckin, checkinPending}: Props) {
  if (error) {
    return (
      <View style={styles.center} testID="board-error">
        <Text style={styles.h2}>The television cannot reach Vita Heart right now.</Text>
        <Text style={styles.body}>{error}</Text>
      </View>
    );
  }
  if (!board) {
    return (
      <View style={styles.center} testID="board-loading">
        <Text style={styles.h2}>One moment…</Text>
      </View>
    );
  }
  const due = board.dueDoses.length;
  return (
    <View style={styles.root} testID="morning-board">
      <View style={styles.header}>
        <Text style={styles.greeting} testID="greeting">{board.greeting}</Text>
        <Text style={styles.live} testID="live-state">{live === 'live' ? '● live' : live === 'retrying' ? '○ reconnecting' : '○ connecting'}</Text>
      </View>

      <View style={styles.row}>
        <Card title="Today" style={styles.grow} testID="card-today">
          <Text style={styles.h1}>{due === 0 ? 'Nothing due right now' : `${due} to take`}</Text>
          <Text style={styles.body}>Medication reminders arrive here once the boxes are photographed.</Text>
        </Card>
        <Card title="Resting heart rate" testID="card-hr">
          <Text style={[styles.hero, {color: color.heart}]}>{board.restingHeartRate ?? '—'}</Text>
          <Text style={styles.small}>beats per minute, last night</Text>
        </Card>
      </View>

      <Card title={board.message ? `From ${board.message.author}` : 'Family'} testID="card-message">
        <Text style={styles.h2}>{board.message ? board.message.text : 'No new message.'}</Text>
      </Card>

      <View style={styles.actions}>
        {board.checkedInToday ? (
          <Text style={[styles.h2, {color: color.calm}]} testID="checked-in">✓ You said you are up. {board.family[0]?.name ?? 'The family'} knows.</Text>
        ) : (
          <BigButton label={checkinPending ? 'Telling the family…' : "I'm up"} onPress={onCheckin} hasTVPreferredFocus testID="checkin" disabled={checkinPending} />
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, gap: space.l},
  center: {flex: 1, justifyContent: 'center', gap: space.m},
  header: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-end'},
  greeting: {color: color.text, fontSize: type.h1, fontWeight: '700'},
  live: {color: color.textDim, fontSize: type.small},
  row: {flexDirection: 'row', gap: space.l},
  grow: {flex: 1},
  hero: {fontSize: type.hero, fontWeight: '700', lineHeight: type.hero * 1.05},
  h1: {color: color.text, fontSize: type.h2, fontWeight: '700'},
  h2: {color: color.text, fontSize: type.body, lineHeight: type.body * 1.35},
  body: {color: color.textDim, fontSize: type.small, lineHeight: type.small * 1.4},
  small: {color: color.textDim, fontSize: type.small},
  actions: {marginTop: 'auto'},
});
