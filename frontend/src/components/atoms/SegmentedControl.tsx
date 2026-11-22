import React, { useLayoutEffect, useState } from 'react';
import {
  Animated,
  Easing,
  LayoutChangeEvent,
  Platform,
  Pressable,
  StyleProp,
  StyleSheet,
  View,
  ViewStyle,
} from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import { colors, gradients } from '@theme/index';
import AppText from './Text';

export interface SegmentOption<T extends string> {
  value: T;
  label: string;
}

export interface SegmentedControlProps<T extends string> {
  options: SegmentOption<T>[];
  value: T;
  onChange: (value: T) => void;
  /** Set for a switch inside scrolling content: it then waits for the tap, so a scroll can't change it. */
  scrollable?: boolean;
  style?: StyleProp<ViewStyle>;
}

const SLIDE_DURATION_MS = 200;

// react-native-web waits 50 ms before reporting a press-in (native reports it at once). Pinned tabs sit
// outside any scroll view, so there is no scroll gesture to wait for: report it immediately.
// `delayPressIn` is web-only and missing from React Native's types, hence the spread.
const IMMEDIATE_PRESS_IN = Platform.OS === 'web' ? { delayPressIn: 0 } : {};

/** Equal-width single-choice switch, e.g. All / Expenses / Income. The highlight slides to the chosen segment. */
const SegmentedControl = <T extends string>({
  options,
  value,
  onChange,
  scrollable = false,
  style,
}: SegmentedControlProps<T>) => {
  const count = options.length;
  const selectedIndex = Math.max(0, options.findIndex((option) => option.value === value));
  const [position] = useState(() => new Animated.Value(selectedIndex));
  const [segmentWidth, setSegmentWidth] = useState(0);

  // Layout effect + native driver: the slide starts in the tap's frame and keeps running smoothly
  // while the JS thread renders the newly selected content.
  useLayoutEffect(() => {
    const slide = Animated.timing(position, {
      toValue: selectedIndex,
      duration: SLIDE_DURATION_MS,
      easing: Easing.out(Easing.cubic),
      useNativeDriver: true,
    });
    slide.start();
    return () => slide.stop();
  }, [position, selectedIndex]);

  const onLayout = (event: LayoutChangeEvent) => setSegmentWidth(event.nativeEvent.layout.width / count);

  // Until the width is measured (first frame), place the highlight by percentage instead.
  const placement = segmentWidth
    ? { transform: [{ translateX: position.interpolate({ inputRange: [0, 1], outputRange: [0, segmentWidth] }) }] }
    : { left: `${(100 * selectedIndex) / count}%` as const };

  return (
    <View style={[styles.track, style]} accessibilityRole="tablist">
      <View style={styles.segments} onLayout={onLayout}>
        <Animated.View style={[styles.highlight, { width: `${100 / count}%` }, placement]}>
          <LinearGradient
            colors={gradients.icon.colors}
            start={gradients.icon.start}
            end={gradients.icon.end}
            style={styles.highlightFill}
          />
        </Animated.View>
        {options.map((option) => {
          const selected = option.value === value;
          const select = () => {
            if (!selected) onChange(option.value);
          };
          return (
            <Pressable
              key={option.value}
              // Pinned tabs switch on touch-down so the change feels instant; onPress covers screen-reader activation.
              onPressIn={scrollable ? undefined : select}
              onPress={select}
              {...(scrollable ? null : IMMEDIATE_PRESS_IN)}
              accessibilityRole="tab"
              // The aria prop, because react-native-web ignores `accessibilityState`.
              aria-selected={selected}
              style={styles.segment}
            >
              <AppText
                variant="subheading13"
                align="center"
                color={selected ? colors.text.inverse : colors.text.secondary}
              >
                {option.label}
              </AppText>
            </Pressable>
          );
        })}
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  track: {
    width: '100%',
    padding: 4,
    borderRadius: 14,
    backgroundColor: colors.surfaceMuted,
  },
  segments: { flexDirection: 'row' },
  highlight: { position: 'absolute', top: 0, bottom: 0, left: 0, pointerEvents: 'none' },
  highlightFill: { flex: 1, borderRadius: 10 },
  segment: {
    flex: 1,
    minHeight: 40,
    justifyContent: 'center',
    paddingHorizontal: 6,
  },
});

export default SegmentedControl;
