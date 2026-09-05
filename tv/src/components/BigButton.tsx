import React, {useState} from 'react';
import {Pressable, StyleSheet, Text} from 'react-native';
import {color, focus, radius, space, type} from '../design/tokens';

type Props = {
  label: string;
  onPress: () => void;
  tone?: 'warm' | 'calm' | 'quiet';
  hasTVPreferredFocus?: boolean;
  testID?: string;
  disabled?: boolean;
};

/** One button shape for the whole app: big, high contrast, obvious focus. */
export function BigButton({label, onPress, tone = 'warm', hasTVPreferredFocus, testID, disabled}: Props) {
  const [focused, setFocused] = useState(false);
  const bg = tone === 'calm' ? color.calm : tone === 'quiet' ? color.panelRaised : color.warm;
  const fg = tone === 'quiet' ? color.text : color.ground;
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
        {backgroundColor: bg},
        disabled && styles.disabled,
        focused && styles.focused,
      ]}>
      <Text style={[styles.label, {color: fg}]}>{label}</Text>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  base: {
    paddingVertical: space.m,
    paddingHorizontal: space.xl,
    borderRadius: radius.pill,
    borderWidth: focus.ring,
    borderColor: 'transparent',
    alignSelf: 'flex-start',
  },
  label: {fontSize: type.body, fontWeight: '700'},
  disabled: {opacity: 0.5},
  focused: {borderColor: color.text, transform: [{scale: focus.scale}]},
});
