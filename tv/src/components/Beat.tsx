import React, {useEffect, useRef} from 'react';
import {Animated, Easing, StyleSheet, Text, View} from 'react-native';
import {Icon} from './Icon';
import {color, s} from '../design/tokens';

/**
 * The screen beats at the heart's own rate.
 *
 * Period is 60/bpm, so at 77 the halo opens every 0.78 s and at 104 every 0.58 s:
 * the room can see the effort rise before the number is read. A still number is a
 * readout; a number that beats is the person. Nothing here is decorative timing —
 * if the wrist stops sending, the beating stops with it.
 */
export function useBeat(bpm: number | null) {
  const beat = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    if (!bpm) {
      beat.setValue(0);
      return;
    }
    const period = Math.max(320, Math.min(2000, 60000 / bpm));
    const anim = Animated.loop(
      Animated.sequence([
        // systole: fast, the way a pulse actually feels
        Animated.timing(beat, {toValue: 1, duration: Math.round(period * 0.16),
          easing: Easing.out(Easing.quad), useNativeDriver: true}),
        Animated.timing(beat, {toValue: 0, duration: Math.round(period * 0.84),
          easing: Easing.out(Easing.cubic), useNativeDriver: true}),
      ]),
    );
    anim.start();
    return () => { anim.stop(); };
  }, [bpm, beat]);
  return beat;
}

/** The number, beating. Its own scale only — the rings behind it do the loud part. */
export function BeatingNumber({bpm, style, testID, children}: {
  bpm: number | null; style?: any; testID?: string; children: React.ReactNode;
}) {
  const beat = useBeat(bpm);
  const scale = beat.interpolate({inputRange: [0, 1], outputRange: [1, 1.035]});
  return (
    <Animated.Text testID={testID} style={[style, {transform: [{scale}]}]}>{children}</Animated.Text>
  );
}

/**
 * Two rings leaving the number on every beat.
 *
 * A filled disc behind a number is a shape sitting on a card. A ring that leaves and
 * fades is a pulse travelling, which is the thing being measured — and at ten feet,
 * across a room, the movement is what carries, not the shape. A dim ring stays at rest
 * so the card is never empty between beats or when no wrist is sending.
 */
export function PulseRings({bpm, size}: {bpm: number | null; size: number}) {
  const beat = useBeat(bpm);
  const round = (d: number) => ({width: d, height: d, borderRadius: d / 2});
  const core = {
    opacity: beat.interpolate({inputRange: [0, 1], outputRange: [0.10, 0.20]}),
    transform: [{scale: beat.interpolate({inputRange: [0, 1], outputRange: [1, 1.06]})}],
  };
  const inner = {
    opacity: beat.interpolate({inputRange: [0, 0.3, 1], outputRange: [0, 0.55, 0]}),
    transform: [{scale: beat.interpolate({inputRange: [0, 1], outputRange: [0.66, 1.16]})}],
  };
  const outer = {
    opacity: beat.interpolate({inputRange: [0, 0.25, 1], outputRange: [0, 0.42, 0]}),
    transform: [{scale: beat.interpolate({inputRange: [0, 1], outputRange: [0.8, 1.46]})}],
  };
  return (
    <View pointerEvents="none" style={[styles.rings, round(size)]}>
      <View style={[styles.rest, round(size)]} />
      <Animated.View style={[styles.core, round(size * 0.84), core]} />
      <Animated.View style={[styles.wave, round(size), inner, {borderWidth: Math.max(2, s(4))}]} />
      <Animated.View style={[styles.wave, round(size), outer, {borderWidth: Math.max(1, s(2.5))}]} />
    </View>
  );
}

/** The card's own eyebrow, with a heart that beats where a static one would sit. */
export function BeatingEyebrow({bpm, children}: {bpm: number | null; children: string}) {
  const beat = useBeat(bpm);
  const scale = beat.interpolate({inputRange: [0, 1], outputRange: [1, 1.22]});
  const opacity = beat.interpolate({inputRange: [0, 1], outputRange: [0.72, 1]});
  return (
    <View style={styles.eyebrow}>
      <Animated.View style={{opacity, transform: [{scale}]}}>
        <Icon name="heart" size={s(26)} tint={color.heart} width={2.4} />
      </Animated.View>
      <Text style={styles.eyebrowText}>{children.toUpperCase()}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  eyebrow: {flexDirection: 'row', alignItems: 'center', gap: s(12), alignSelf: 'flex-start'},
  eyebrowText: {fontSize: s(26), letterSpacing: s(3), fontWeight: '700', color: color.dim2},
  rings: {position: 'absolute', alignItems: 'center', justifyContent: 'center'},
  rest: {position: 'absolute', borderWidth: Math.max(1, s(2)), borderColor: 'rgba(255,111,97,0.20)'},
  core: {position: 'absolute', backgroundColor: color.heart},
  wave: {position: 'absolute', borderColor: color.heart},
});
