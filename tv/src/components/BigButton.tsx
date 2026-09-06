import React, {useState} from 'react';
import {Pressable, StyleSheet, Text} from 'react-native';
import {Icon, IconName} from './Icon';
import {color, focus, radius} from '../design/tokens';

type Tone = 'warm' | 'quiet' | 'calm' | 'heart';
const TONE = {
  warm: {bg: color.warm, fg: color.warmInk, edge: 'transparent'},
  calm: {bg: color.calm, fg: color.calmInk, edge: 'transparent'},
  heart: {bg: color.heart, fg: color.heartInk, edge: 'transparent'},
  quiet: {bg: color.panel2, fg: color.text, edge: color.hair2},
} as const;

/**
 * One button shape for the whole product. Focus is a white ring plus a small
 * lift, so it reads without relying on colour, and the label never wraps.
 */
export function BigButton({
  label, onPress, icon, tone = 'warm', hasTVPreferredFocus, testID, disabled, compact,
}: {
  label: string; onPress: () => void; icon?: IconName; tone?: Tone;
  hasTVPreferredFocus?: boolean; testID?: string; disabled?: boolean; compact?: boolean;
}) {
  const [focused, setFocused] = useState(false);
  const t = TONE[tone];
  return (
    <Pressable
      onPress={disabled ? undefined : onPress}
      onFocus={() => setFocused(true)}
      onBlur={() => setFocused(false)}
      hasTVPreferredFocus={hasTVPreferredFocus}
      accessibilityRole="button"
      accessibilityLabel={label}
      testID={testID}
      style={[
        styles.base,
        compact ? styles.compact : null,
        {backgroundColor: t.bg, borderColor: t.edge},
        disabled ? styles.disabled : null,
        focused ? styles.focused : null,
      ]}>
      {icon ? <Icon name={icon} size={compact ? 26 : 30} tint={t.fg} width={2.4} /> : null}
      <Text numberOfLines={1} style={[styles.label, compact ? styles.labelCompact : null, {color: t.fg}]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {flexDirection: 'row', alignItems: 'center', gap: 16, paddingVertical: 23, paddingHorizontal: 42,
    borderRadius: radius.pill, borderWidth: 1, alignSelf: 'flex-start'},
  compact: {paddingVertical: 18, paddingHorizontal: 30},
  label: {fontSize: 33, fontWeight: '700'},
  labelCompact: {fontSize: 26},
  disabled: {opacity: 0.5},
  focused: {borderColor: '#FFFFFF', borderWidth: focus.ring, transform: [{scale: focus.scale}]},
});
