import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {radius} from '../design/tokens';

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
  band: {position: 'absolute', left: 0, right: 0, top: 0, height: 32},
  name: {position: 'absolute', left: 15, right: 15, top: 44, color: '#1B1A17', fontWeight: '700', fontSize: 24, lineHeight: 27},
  mg: {position: 'absolute', left: 15, bottom: 13, color: '#5C574E', fontWeight: '600', fontSize: 19},
  bars: {position: 'absolute', right: 13, bottom: 13, flexDirection: 'row', gap: 3},
  bar: {width: 3, height: 22, backgroundColor: '#1B1A17'},
});
