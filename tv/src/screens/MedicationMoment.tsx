import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {Dose} from '../api/client';
import {BigButton} from '../components/BigButton';
import {BoxThumb} from '../components/BoxThumb';
import {Card, Eyebrow} from '../components/Card';
import {Chip} from '../components/Chip';
import {Icon} from '../components/Icon';
import {color, type} from '../design/tokens';

type Props = {doses: Dose[]; onConfirm: (d: Dose) => void; onBack: () => void; onSetClock: () => void; pendingId: string | null};

const SLOT: Record<string, string> = {morning: 'Morning', midday: 'Midday', evening: 'Evening', night: 'Night'};
const BANDS = ['#E2452F', '#2E6FB7', '#5B8C3E', '#8A4FBF'];

/**
 * One dose per card, one button per card. The recall line never says "recalled":
 * it hands over the question to ask the pharmacist.
 */
export function MedicationMoment({doses, onConfirm, onBack, onSetClock, pendingId}: Props) {
  const open = doses.filter(d => !d.confirmed);
  const unscheduled = doses.some(d => d.unscheduled);
  return (
    <View style={styles.wrap} testID="medication-moment">
      <View style={styles.list}>
        {doses.slice(0, 2).map((d, i) => (
          <Card key={d.id} tint={d.confirmed ? 'plain' : 'warm'} style={[styles.med, d.confirmed ? styles.taken : null]} testID={`dose-${d.id}`}>
            <View style={styles.top}>
              <BoxThumb name={d.name || 'Unreadable'} strength={d.strength} band={BANDS[i % BANDS.length]} width={172} height={124} />
              <View style={styles.info}>
                <Text style={styles.h3} numberOfLines={2}>{d.name || 'Unreadable box'}{d.strength ? ` ${d.strength}` : ''}</Text>
                <Text style={styles.meta}>one tablet{d.food ? ` · ${d.food}` : ''}</Text>
                <Text style={[styles.meta, d.confirmed ? null : styles.metaWarm]}>
                  {SLOT[d.slot] ?? d.slot}{d.dueAt ? `, ${d.dueAt.slice(11, 16)}` : ' · time not set yet'}
                </Text>
              </View>
            </View>

            {d.recallCount > 0 ? (
              <View style={styles.safety}>
                <Icon name="shield" size={28} tint={color.warm} />
                <Text style={styles.safetyText}>A batch of this ingredient was recalled. Ask the pharmacist: “is my lot affected?” Do not stop taking it on your own.</Text>
              </View>
            ) : (
              <Chip icon="check" tone="calm">Nothing on the safety record today</Chip>
            )}

            {d.confirmed ? (
              <View style={styles.done}><Icon name="check" size={30} tint={color.calm} /><Text style={styles.doneText}>Taken</Text></View>
            ) : (
              <BigButton
                label={pendingId === d.id ? 'Saving…' : 'I took it'}
                icon="check" tone="warm" onPress={() => onConfirm(d)}
                hasTVPreferredFocus={i === 0} disabled={pendingId !== null} testID={`confirm-${d.id}`}
              />
            )}
          </Card>
        ))}
      </View>

      <Card tint="sky" style={styles.strip}>
        <View style={styles.stripText}>
          <Eyebrow icon="camera">How a box gets here</Eyebrow>
          <Text style={styles.stripH}>The family photographs the packet once, from a phone</Text>
        </View>
        <View style={styles.stripChips}>
          <Chip>Reader · Nova Lite</Chip>
          <Chip>Identifier · RxNorm</Chip>
          <Chip>Watchman · openFDA</Chip>
        </View>
      </Card>

      <View style={styles.footer}>
        {unscheduled ? <BigButton label="Set my times" icon="clock" compact onPress={onSetClock} testID="set-clock" /> : null}
        <BigButton label="Back" tone="quiet" compact onPress={onBack} testID="back" />
        <Text style={styles.count}>{open.length ? `${open.length} still to take` : 'All taken'}</Text>
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {flex: 1, gap: 24},
  list: {flex: 1, flexDirection: 'row', gap: 24},
  med: {flex: 1, gap: 22, paddingVertical: 34, paddingHorizontal: 36},
  taken: {opacity: 0.72},
  top: {flexDirection: 'row', gap: 26, alignItems: 'flex-start'},
  info: {flex: 1},
  h3: {fontFamily: 'serif', fontSize: type.h3, lineHeight: 45, color: color.text},
  meta: {fontSize: type.small, lineHeight: 34, color: color.dim},
  metaWarm: {color: color.warm2},
  safety: {flexDirection: 'row', gap: 14, alignItems: 'flex-start', paddingVertical: 20, paddingHorizontal: 24,
    borderRadius: 20, backgroundColor: color.warmSoft, borderWidth: 1, borderColor: color.warmEdge},
  safetyText: {flex: 1, fontSize: 24, lineHeight: 32, color: color.warmText},
  done: {flexDirection: 'row', alignItems: 'center', gap: 14, marginTop: 'auto'},
  doneText: {fontSize: type.body, fontWeight: '600', color: color.calm},
  strip: {height: 152, flexDirection: 'row', alignItems: 'center', gap: 36, paddingVertical: 26, paddingHorizontal: 36},
  stripText: {flex: 1},
  stripH: {fontFamily: 'serif', fontSize: 32, lineHeight: 40, color: color.text, marginTop: 10},
  stripChips: {flexDirection: 'row', gap: 14},
  footer: {flexDirection: 'row', alignItems: 'center', gap: 20},
  count: {marginLeft: 'auto', fontSize: 23, color: color.dim2},
});
