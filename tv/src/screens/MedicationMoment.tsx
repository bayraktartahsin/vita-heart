import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import type {Dose} from '../api/client';
import {BigButton} from '../components/BigButton';
import {Card} from '../components/Card';
import {color, space, type} from '../design/tokens';

type Props = {
  doses: Dose[];
  onConfirm: (dose: Dose) => void;
  onBack: () => void;
  onSetClock: () => void;
  pendingId: string | null;
};

const SLOT_LABEL: Record<string, string> = {morning: 'Morning', midday: 'Midday', evening: 'Evening', night: 'Night'};

/**
 * One dose per card, one button per card. The recall line never says "recalled":
 * it hands over the question to ask the pharmacist, which is the VitaCabinet rule.
 */
export function MedicationMoment({doses, onConfirm, onBack, onSetClock, pendingId}: Props) {
  const open = doses.filter(d => !d.confirmed);
  const unscheduled = doses.some(d => d.unscheduled);
  return (
    <View style={styles.root} testID="medication-moment">
      <Text style={styles.h1}>{open.length === 0 ? 'All taken. Well done.' : open.length === 1 ? 'One to take' : `${open.length} to take`}</Text>
      <View style={styles.list}>
        {doses.map((d, i) => (
          <Card key={d.id} title={`${SLOT_LABEL[d.slot] ?? d.slot}${d.dueAt ? '' : ' · time not set yet'}`} testID={`dose-${d.id}`}>
            <Text style={styles.name}>{d.name ?? 'Unreadable box'}{d.strength ? `  ${d.strength}` : ''}</Text>
            {d.food ? <Text style={styles.body}>{d.food === 'with food' ? 'With food.' : 'Before food.'}</Text> : null}
            {d.status === 'unconfirmed' ? <Text style={styles.body}>Read from the box, not yet confirmed by the pharmacist database.</Text> : null}
            {d.recallCount > 0 ? (
              <Text style={[styles.body, {color: color.attention}]}>A safety notice exists for this ingredient. Ask the pharmacist: "Is my batch affected?"</Text>
            ) : null}
            {d.confirmed ? (
              <Text style={[styles.body, {color: color.calm}]}>✓ Taken</Text>
            ) : (
              <BigButton
                label={pendingId === d.id ? 'Saving…' : 'I took it'}
                tone="calm"
                onPress={() => onConfirm(d)}
                hasTVPreferredFocus={i === 0}
                disabled={pendingId !== null}
                testID={`confirm-${d.id}`}
              />
            )}
          </Card>
        ))}
      </View>
      <View style={styles.footer}>
        {unscheduled ? <BigButton label="Set my times" onPress={onSetClock} testID="set-clock" /> : null}
        <BigButton label="Back" tone="quiet" onPress={onBack} testID="back" />
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, gap: space.l},
  h1: {color: color.text, fontSize: type.h1, fontWeight: '700'},
  list: {flexDirection: 'row', flexWrap: 'wrap', gap: space.l},
  name: {color: color.text, fontSize: type.h2, fontWeight: '700'},
  body: {color: color.textDim, fontSize: type.small, lineHeight: type.small * 1.4},
  footer: {marginTop: 'auto', flexDirection: 'row', gap: space.l},
});
