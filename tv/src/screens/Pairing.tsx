import React, {useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {BigButton} from '../components/BigButton';
import {Card, Eyebrow} from '../components/Card';
import {color, type} from '../design/tokens';

const CHARS = 'ABCDEFGHJKLMNPQRSTUVWXYZ23456789'.split('');

/**
 * Pairing with the remote only: six slots, up/down changes a letter, left/right
 * moves. The code is printed on the family's phone. No keyboard, no typing.
 */
export function Pairing({onPaired, initial = 'AHMET1'}: {onPaired: (code: string) => void; initial?: string}) {
  const [slots, setSlots] = useState(initial.padEnd(6, 'A').slice(0, 6).split(''));
  const bump = (i: number, dir: 1 | -1) =>
    setSlots(s => s.map((c, j) => (j === i ? CHARS[(CHARS.indexOf(c) + dir + CHARS.length) % CHARS.length] : c)));
  return (
    <View style={styles.root} testID="pairing">
      <Card style={styles.card}>
        <Eyebrow icon="family">Connect this television</Eyebrow>
        <Text style={styles.h1}>Enter the code from the family's phone</Text>
        <View style={styles.slots}>
          {slots.map((c, i) => (
            <View key={i} style={styles.slot}>
              <BigButton label="Up" tone="quiet" compact onPress={() => bump(i, 1)} testID={`up-${i}`} />
              <Text style={styles.char}>{c}</Text>
              <BigButton label="Down" tone="quiet" compact onPress={() => bump(i, -1)} testID={`down-${i}`} />
            </View>
          ))}
        </View>
        <BigButton label="Connect" icon="check" onPress={() => onPaired(slots.join(''))} hasTVPreferredFocus testID="connect" />
      </Card>
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, justifyContent: 'center', alignItems: 'center'},
  card: {alignItems: 'center', gap: 28, paddingVertical: 52, paddingHorizontal: 72},
  h1: {fontFamily: 'serif', fontSize: type.h2, lineHeight: 58, color: color.text, textAlign: 'center'},
  slots: {flexDirection: 'row', gap: 20},
  slot: {alignItems: 'center', gap: 14},
  char: {fontFamily: 'serif', fontSize: 104, lineHeight: 112, color: color.warm2, width: 104, textAlign: 'center'},
});
