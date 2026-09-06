import React, {useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {BigButton} from '../components/BigButton';
import {Card, Eyebrow} from '../components/Card';
import {color, type} from '../design/tokens';

export const SLOTS = ['morning', 'midday', 'evening', 'night'] as const;
export type Slot = (typeof SLOTS)[number];
const LABEL: Record<Slot, string> = {morning: 'Morning', midday: 'Midday', evening: 'Evening', night: 'Night'};
const PROPOSED: Record<Slot, string> = {morning: '08:00', midday: '13:00', evening: '19:00', night: '22:00'};

export function shift(hhmm: string, minutes: number): string {
  const [h, m] = hhmm.split(':').map(Number);
  const total = (((h * 60 + m + minutes) % 1440) + 1440) % 1440;
  return `${String(Math.floor(total / 60)).padStart(2, '0')}:${String(total % 60).padStart(2, '0')}`;
}

/**
 * The household maps slots to its own clock, once. The label said "twice daily";
 * nobody decided 09:00 for Ahmet. He does, here, with two arrow keys.
 */
export function ClockSetup({slotsNeeded, initial = {}, onConfirm, onBack, pending}: {
  slotsNeeded: Slot[]; initial?: Partial<Record<Slot, string>>;
  onConfirm: (t: Record<string, string>) => void; onBack: () => void; pending: boolean;
}) {
  const [times, setTimes] = useState<Record<Slot, string>>(() => {
    const t = {...PROPOSED};
    SLOTS.forEach(s => {
      if (initial[s]) {
        t[s] = initial[s] as string;
      }
    });
    return t;
  });
  const bump = (s: Slot, min: number) => setTimes(t => ({...t, [s]: shift(t[s], min)}));
  const slots = slotsNeeded.length ? slotsNeeded : (['morning'] as Slot[]);

  return (
    <View style={styles.wrap} testID="clock-setup">
      <Text style={styles.lead}>These are suggestions, not decisions. Move them to your own day; you can come back any time.</Text>
      <View style={styles.row}>
        {slots.map((s, i) => (
          <Card key={s} style={styles.slot} testID={`slot-${s}`}>
            <Eyebrow icon="clock">{LABEL[s]}</Eyebrow>
            <BigButton label="Later" icon="arrow" tone="quiet" compact onPress={() => bump(s, 30)} hasTVPreferredFocus={i === 0} testID={`later-${s}`} />
            <Text style={styles.time} testID={`time-${s}`}>{times[s]}</Text>
            <BigButton label="Earlier" icon="arrow" tone="quiet" compact onPress={() => bump(s, -30)} testID={`earlier-${s}`} />
          </Card>
        ))}
      </View>
      <View style={styles.actions}>
        <BigButton label={pending ? 'Saving…' : 'These are my times'} icon="check" tone="calm" disabled={pending}
          onPress={() => onConfirm(Object.fromEntries(slots.map(s => [s, times[s]])))} testID="confirm-clock" />
        <BigButton label="Back" tone="quiet" onPress={onBack} testID="back" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {flex: 1, gap: 30},
  lead: {fontSize: type.body, lineHeight: 41, color: color.dim, maxWidth: 1250},
  row: {flexDirection: 'row', gap: 26},
  slot: {flex: 1, alignItems: 'center', gap: 20},
  time: {fontFamily: 'serif', fontSize: 108, lineHeight: 116, color: color.warm2, letterSpacing: -3},
  actions: {flexDirection: 'row', gap: 22, marginTop: 'auto'},
});
