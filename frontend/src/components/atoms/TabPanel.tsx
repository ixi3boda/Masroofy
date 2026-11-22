import React, { ReactNode, useLayoutEffect, useRef, useState } from 'react';
import { Animated, Easing, StyleSheet } from 'react-native';
import { spacing } from '@theme/index';

export interface TabPanelProps {
  /** Position of the selected tab (0, 1, …). A change replays the enter animation from that tab's side. */
  index: number;
  children: ReactNode;
  /** Vertical space between the panel's sections; matches ScreenLayout's default. */
  gap?: number;
}

// Short and starting partly visible, so the switch reads as immediate rather than delayed.
const ENTER_DURATION_MS = 170;
const ENTER_FROM_OPACITY = 0.35;
const SLIDE_DISTANCE = 12;

/**
 * Body of the selected tab. When the tab changes, the new content fades in and
 * slides from the side it lives on (right when moving forward, left when back),
 * following the SegmentedControl highlight.
 */
const TabPanel: React.FC<TabPanelProps> = ({ index, children, gap = spacing.xl }) => {
  const [opacity] = useState(() => new Animated.Value(1));
  const [offset] = useState(() => new Animated.Value(0));
  const shownIndex = useRef(index);

  // Layout effect: the new content must start hidden before the first paint, or it flashes in.
  useLayoutEffect(() => {
    if (shownIndex.current === index) return undefined;
    const direction = index > shownIndex.current ? 1 : -1;
    shownIndex.current = index;

    opacity.setValue(ENTER_FROM_OPACITY);
    offset.setValue(direction * SLIDE_DISTANCE);
    const timing = { duration: ENTER_DURATION_MS, easing: Easing.out(Easing.cubic), useNativeDriver: true };
    const enter = Animated.parallel([
      Animated.timing(opacity, { ...timing, toValue: 1 }),
      Animated.timing(offset, { ...timing, toValue: 0 }),
    ]);
    enter.start();
    return () => enter.stop();
  }, [index, opacity, offset]);

  return (
    <Animated.View style={[styles.panel, { gap, opacity, transform: [{ translateX: offset }] }]}>
      {children}
    </Animated.View>
  );
};

const styles = StyleSheet.create({
  panel: { width: '100%' },
});

export default TabPanel;
