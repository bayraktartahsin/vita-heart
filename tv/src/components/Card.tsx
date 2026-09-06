import React from 'react';
import {StyleProp, StyleSheet, Text, View, ViewStyle} from 'react-native';
import {Icon, IconName} from './Icon';
import {color, radius, type} from '../design/tokens';

type Tint = 'plain' | 'warm' | 'heart' | 'sky';

const TINT: Record<Tint, {bg: string; edge: string}> = {
  plain: {bg: color.panel, edge: color.hair},
  warm: {bg: color.warmSoft, edge: color.warmEdge},
  heart: {bg: color.heartSoft, edge: color.heartEdge},
  sky: {bg: color.skySoft, edge: color.skyEdge},
};

export function Eyebrow({icon, children}: {icon?: IconName; children: React.ReactNode}) {
  return (
    <View style={styles.eyebrow}>
      {icon ? <Icon name={icon} size={26} /> : null}
      <Text style={styles.eyebrowText}>{String(children).toUpperCase()}</Text>
    </View>
  );
}

export function Card({tint = 'plain', style, children, testID}: {tint?: Tint; style?: StyleProp<ViewStyle>; children: React.ReactNode; testID?: string}) {
  const t = TINT[tint];
  return (
    <View testID={testID} style={[styles.card, {backgroundColor: t.bg, borderColor: t.edge}, style]}>
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {borderRadius: radius.card, borderWidth: 1, paddingVertical: 36, paddingHorizontal: 40, gap: 18, overflow: 'hidden'},
  eyebrow: {flexDirection: 'row', alignItems: 'center', gap: 14},
  eyebrowText: {fontSize: type.micro, letterSpacing: 3.4, color: color.dim, fontWeight: '600'},
});
