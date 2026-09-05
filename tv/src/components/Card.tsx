import React from 'react';
import {StyleSheet, Text, View, ViewStyle} from 'react-native';
import {color, radius, space, type} from '../design/tokens';

type Props = {title?: string; children: React.ReactNode; style?: ViewStyle; testID?: string};

export function Card({title, children, style, testID}: Props) {
  return (
    <View style={[styles.card, style]} testID={testID}>
      {title ? <Text style={styles.title}>{title}</Text> : null}
      {children}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {backgroundColor: color.panel, borderRadius: radius.card, padding: space.l, gap: space.s},
  title: {color: color.textDim, fontSize: type.small, letterSpacing: 1.5, textTransform: 'uppercase'},
});
