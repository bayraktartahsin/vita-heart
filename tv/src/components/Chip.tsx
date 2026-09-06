import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {Icon, IconName} from './Icon';
import {color, radius, type} from '../design/tokens';

type Tone = 'plain' | 'calm' | 'warm' | 'heart';
const TONE = {
  plain: {bg: color.panel2, edge: color.hair, fg: color.text},
  calm: {bg: color.calmSoft, edge: color.calmEdge, fg: color.calm},
  warm: {bg: color.warmSoft, edge: color.warmEdge, fg: color.warmText},
  heart: {bg: color.heartSoft, edge: color.heartEdge, fg: color.heart},
} as const;

export function Chip({icon, tone = 'plain', children, style, testID}: {icon?: IconName; tone?: Tone; children: React.ReactNode; style?: object; testID?: string}) {
  const t = TONE[tone];
  return (
    <View testID={testID} style={[styles.chip, {backgroundColor: t.bg, borderColor: t.edge}, style]}>
      {icon ? <Icon name={icon} size={24} tint={t.fg} /> : null}
      <Text style={[styles.text, {color: t.fg}]}>{children}</Text>
    </View>
  );
}

const styles = StyleSheet.create({
  chip: {flexDirection: 'row', alignItems: 'center', gap: 11, paddingVertical: 12, paddingHorizontal: 18,
    borderRadius: radius.chip, borderWidth: 1, alignSelf: 'flex-start'},
  text: {fontSize: type.label, fontWeight: '600'},
});
