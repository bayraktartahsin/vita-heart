import React, {useState} from 'react';
import {LayoutChangeEvent, StyleSheet, View} from 'react-native';
import Svg, {Defs, LinearGradient, Rect, RadialGradient, Stop} from '@amazon-devices/react-native-svg';
import {color} from '../design/tokens';

/**
 * The room behind the content: a warm light top right, a cool one bottom left,
 * over a near-black gradient.
 *
 * The Svg is sized in pixels from onLayout rather than "100%": the Vega SVG
 * runtime logs "rerender view parent is null" and skips a percentage-sized root,
 * so a measured size is the difference between a lit room and a black rectangle.
 */
export function Backdrop() {
  const [size, setSize] = useState<{w: number; h: number} | null>(null);
  const onLayout = (e: LayoutChangeEvent) => {
    const {width, height} = e.nativeEvent.layout;
    if (width > 0 && height > 0 && (!size || size.w !== width || size.h !== height)) {
      setSize({w: width, h: height});
    }
  };
  return (
    <View style={[StyleSheet.absoluteFill, {backgroundColor: color.ink2}]} pointerEvents="none" onLayout={onLayout}>
      {size ? (
        <Svg width={size.w} height={size.h}>
          <Defs>
            <LinearGradient id="ground" x1="0" y1="0" x2={String(size.w * 0.3)} y2={String(size.h)} gradientUnits="userSpaceOnUse">
              <Stop offset="0" stopColor="#11161D" />
              <Stop offset="0.58" stopColor="#0A0D12" />
              <Stop offset="1" stopColor="#07090C" />
            </LinearGradient>
            <RadialGradient id="warm" cx={String(size.w * 0.84)} cy={String(-size.h * 0.06)} r={String(size.w * 0.55)} gradientUnits="userSpaceOnUse">
              <Stop offset="0" stopColor="#F5B14C" stopOpacity="0.14" />
              <Stop offset="1" stopColor="#F5B14C" stopOpacity="0" />
            </RadialGradient>
            <RadialGradient id="cool" cx={String(-size.w * 0.06)} cy={String(size.h * 1.06)} r={String(size.w * 0.5)} gradientUnits="userSpaceOnUse">
              <Stop offset="0" stopColor="#7FC1FF" stopOpacity="0.10" />
              <Stop offset="1" stopColor="#7FC1FF" stopOpacity="0" />
            </RadialGradient>
          </Defs>
          <Rect x="0" y="0" width={size.w} height={size.h} fill="url(#ground)" />
          <Rect x="0" y="0" width={size.w} height={size.h} fill="url(#warm)" />
          <Rect x="0" y="0" width={size.w} height={size.h} fill="url(#cool)" />
        </Svg>
      ) : null}
    </View>
  );
}
