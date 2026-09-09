import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {s, radius} from '../design/tokens';

/**
 * The packet as it looks in the kitchen drawer. Older people match the box, not
 * the word: showing it is the difference between "which one is that?" and "that one".
 */
export function BoxThumb({name, strength, band = '#E2452F', width = 186, height = 132}: {
  name: string; strength?: string | null; band?: string; width?: number; height?: number;
}) {
  return (
    <View style={[styles.box, {width, height}]}>
      <View style={[styles.band, {backgroundColor: band}]} />
      <Text numberOfLines={2} style={styles.name}>{(name || 'UNREADABLE').toUpperCase()}</Text>
      <Text numberOfLines={1} style={styles.mg}>{strength || ''}</Text>
      <View style={styles.bars}>
        {Array.from({length: 7}).map((_, i) => <View key={i} style={styles.bar} />)}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {borderRadius: radius.box, backgroundColor: '#F4EFE5', overflow: 'hidden'},
  band: {position: 'absolute', left: s(0), right: s(0), top: s(0), height: s(32)},
  name: {position: 'absolute', left: s(15), right: s(15), top: s(44), color: '#1B1A17', fontWeight: '700', fontSize: s(24), lineHeight: s(27)},
  mg: {position: 'absolute', left: s(15), bottom: s(13), color: '#5C574E', fontWeight: '600', fontSize: s(19)},
  bars: {position: 'absolute', right: s(13), bottom: s(13), flexDirection: 'row', gap: s(3)},
  bar: {width: s(3), height: s(22), backgroundColor: '#1B1A17'},
});
