import React, {useState} from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {BigButton} from '../components/BigButton';
import {color, space, type} from '../design/tokens';

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
      <Text style={styles.h1}>Enter the code from the family's phone</Text>
      <View style={styles.slots}>
        {slots.map((c, i) => (
          <View key={i} style={styles.slot}>
            <BigButton label="▲" tone="quiet" onPress={() => bump(i, 1)} testID={`up-${i}`} />
            <Text style={styles.char}>{c}</Text>
            <BigButton label="▼" tone="quiet" onPress={() => bump(i, -1)} testID={`down-${i}`} />
          </View>
        ))}
      </View>
      <BigButton label="Connect" onPress={() => onPaired(slots.join(''))} hasTVPreferredFocus testID="connect" />
    </View>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, justifyContent: 'center', alignItems: 'center', gap: space.xl},
  h1: {color: color.text, fontSize: type.h2, fontWeight: '700'},
  slots: {flexDirection: 'row', gap: space.m},
  slot: {alignItems: 'center', gap: space.s},
  char: {color: color.warm, fontSize: type.hero, fontWeight: '700', width: 110, textAlign: 'center'},
});
