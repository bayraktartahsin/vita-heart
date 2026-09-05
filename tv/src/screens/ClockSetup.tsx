import React, {useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {BigButton} from '../components/BigButton';
import {Card} from '../components/Card';
import {color, space, type} from '../design/tokens';

export const SLOTS = ['morning', 'midday', 'evening', 'night'] as const;
export type Slot = (typeof SLOTS)[number];
const LABEL: Record<Slot, string> = {morning: 'Morning', midday: 'Midday', evening: 'Evening', night: 'Night'};
const PROPOSED: Record<Slot, string> = {morning: '08:00', midday: '13:00', evening: '19:00', night: '22:00'};

export function shift(hhmm: string, minutes: number): string {
  const [h, m] = hhmm.split(':').map(Number);
  const total = (((h * 60 + m + minutes) % 1440) + 1440) % 1440;
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

type Props = {
  slotsNeeded: Slot[];
  initial?: Partial<Record<Slot, string>>;
  onConfirm: (times: Record<string, string>) => void;
  onBack: () => void;
  pending: boolean;
};

/**
 * The household maps slots to its own clock, once. The label said "twice daily";
 * nobody decided 09:00 for Ahmet. He does, here, with two arrow keys.
 */
export function ClockSetup({slotsNeeded, initial = {}, onConfirm, onBack, pending}: Props) {
  const [times, setTimes] = useState<Record<Slot, string>>(() => {
    const t = {...PROPOSED};
    for (const s of SLOTS) {
      if (initial[s]) {
        t[s] = initial[s] as string;
      }
    }
    return t;
  });
  const bump = (s: Slot, min: number) => setTimes(t => ({...t, [s]: shift(t[s], min)}));
  return (
    <View style={styles.root} testID="clock-setup">
      <Text style={styles.h1}>When do you usually take them?</Text>
      <Text style={styles.body}>These are suggestions. Change them to your own day; you can always come back.</Text>
      <View style={styles.row}>
        {slotsNeeded.map((s, i) => (
          <Card key={s} title={LABEL[s]} testID={`slot-${s}`}>
            <BigButton label="▲ later" tone="quiet" onPress={() => bump(s, 30)} testID={`later-${s}`} hasTVPreferredFocus={i === 0} />
            <Text style={styles.time} testID={`time-${s}`}>{times[s]}</Text>
            <BigButton label="▼ earlier" tone="quiet" onPress={() => bump(s, -30)} testID={`earlier-${s}`} />
          </Card>
        ))}
      </View>
      <View style={styles.actions}>
        <BigButton label={pending ? 'Saving…' : 'These are my times'} tone="calm" disabled={pending} testID="confirm-clock"
          onPress={() => onConfirm(Object.fromEntries(slotsNeeded.map(s => [s, times[s]])))} />
        <BigButton label="Back" tone="quiet" onPress={onBack} testID="back" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, gap: space.l},
  h1: {color: color.text, fontSize: type.h1, fontWeight: '700'},
  body: {color: color.textDim, fontSize: type.body},
  row: {flexDirection: 'row', gap: space.l},
  time: {color: color.warm, fontSize: type.hero, fontWeight: '700', textAlign: 'center'},
  actions: {marginTop: 'auto', flexDirection: 'row', gap: space.l},
});
