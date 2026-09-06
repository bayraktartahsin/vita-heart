import React from 'react';
import {StyleSheet, Text, View} from 'react-native';
import {Backdrop} from './Backdrop';
import {Icon, IconName} from './Icon';
import {color, type} from '../design/tokens';

const TABS: {key: string; icon: IconName}[] = [
  {key: 'board', icon: 'home'},
  {key: 'meds', icon: 'pill'},
  {key: 'session', icon: 'heart'},
  {key: 'family', icon: 'family'},
];

/**
 * Every screen is the same room: rail on the left, title, content, help line.
 * Consistency is what makes a ten-foot interface learnable in one sitting.
 */
export function Shell({
  tab, title, accent, subtitle, status, children, help, right,
}: {
  tab: string; title: string; accent?: string; subtitle?: string; status?: string;
  children: React.ReactNode; help?: React.ReactNode; right?: React.ReactNode;
}) {
  return (
    <View style={styles.root}>
      <Backdrop />
      <View style={styles.rail}>
        <View style={styles.mark}>
          <Icon name="beat" size={32} tint={color.warmInk} width={2.6} />
        </View>
        <View style={styles.nav}>
          {TABS.map(t => (
            <View key={t.key} style={[styles.navItem, tab === t.key ? styles.navOn : null]}>
              {tab === t.key ? <View style={styles.navBar} /> : null}
              <Icon name={t.icon} size={32} tint={tab === t.key ? color.text : color.dim2} />
            </View>
          ))}
        </View>
        <View style={styles.railFoot}><Icon name="shield" size={26} tint={color.dim2} /></View>
      </View>

      <View style={styles.page}>
        <View style={styles.head}>
          <View style={styles.headText}>
            <Text style={styles.h1} numberOfLines={1}>
              {title}
              {accent ? <Text style={styles.h1accent}>{accent}</Text> : null}
            </Text>
            {subtitle ? <Text style={styles.sub}>{subtitle}</Text> : null}
          </View>
          {right ?? (status ? (
            <View style={styles.live}><View style={styles.liveDot} /><Text style={styles.liveText}>{status}</Text></View>
          ) : null)}
        </View>

        <View style={styles.body}>{children}</View>

        <View style={styles.help}>{help}</View>
      </View>
    </View>
  );
}

export function HelpKeys({items, note}: {items: [string, string][]; note?: string}) {
  return (
    <>
      <View style={styles.helpRow}>
        {items.map(([k, v]) => (
          <View key={k} style={styles.helpItem}>
            <Text style={styles.kbd}>{k}</Text>
            <Text style={styles.helpText}>{v}</Text>
          </View>
        ))}
      </View>
      {note ? <Text style={styles.helpText}>{note}</Text> : null}
    </>
  );
}

const styles = StyleSheet.create({
  root: {flex: 1, flexDirection: 'row', backgroundColor: color.ink},
  rail: {width: 124, paddingTop: 44, paddingBottom: 38, alignItems: 'center', gap: 44,
    borderRightWidth: 1, borderRightColor: color.hair, backgroundColor: 'rgba(0,0,0,0.24)'},
  mark: {width: 60, height: 60, borderRadius: 20, backgroundColor: color.warm, alignItems: 'center', justifyContent: 'center'},
  nav: {gap: 26, marginTop: 6},
  navItem: {width: 68, height: 68, borderRadius: 22, alignItems: 'center', justifyContent: 'center'},
  navOn: {backgroundColor: color.panel2, borderWidth: 1, borderColor: color.hair2},
  navBar: {position: 'absolute', left: -22, top: 19, width: 5, height: 30, borderRadius: 5, backgroundColor: color.warm},
  railFoot: {marginTop: 'auto'},
  page: {flex: 1, paddingTop: 48, paddingBottom: 34, paddingHorizontal: 72, gap: 26},
  head: {flexDirection: 'row', justifyContent: 'space-between', alignItems: 'flex-start'},
  headText: {flex: 1},
  h1: {fontFamily: 'serif', fontSize: type.h1, lineHeight: type.h1, color: color.text, letterSpacing: -2},
  h1accent: {color: color.warm2},
  sub: {marginTop: 12, fontSize: 28, color: color.dim, fontWeight: '500'},
  live: {flexDirection: 'row', alignItems: 'center', gap: 14, paddingVertical: 14, paddingHorizontal: 24,
    borderRadius: 999, backgroundColor: color.panel, borderWidth: 1, borderColor: color.hair},
  liveDot: {width: 12, height: 12, borderRadius: 6, backgroundColor: color.calm},
  liveText: {fontSize: type.small, color: color.dim},
  body: {flex: 1},
  help: {height: 34, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'},
  helpRow: {flexDirection: 'row', gap: 28},
  helpItem: {flexDirection: 'row', alignItems: 'center', gap: 10},
  kbd: {fontSize: 22, fontWeight: '600', color: color.text, backgroundColor: color.panel2,
    borderWidth: 1, borderColor: color.hair, borderRadius: 10, paddingVertical: 5, paddingHorizontal: 13, overflow: 'hidden'},
  helpText: {fontSize: 22, color: color.dim2},
});
