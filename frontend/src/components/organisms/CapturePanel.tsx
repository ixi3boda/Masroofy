import React, { ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { colors, radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Icon, { IconName } from '@components/atoms/Icon';
import ShutterButton from '@components/atoms/ShutterButton';
import { strings } from '@/strings';

export interface CaptureControls {
  onCapture: () => void;
  onRetake?: () => void;
  onToggleFlash?: () => void;
  flashLabel?: string;
}

export interface CapturePanelProps {
  /** Top label, e.g. "Static capture preview" or "Selected receipt". */
  caption: string;
  captionIcon?: IconName;
  /** The framed content — camera preview or the selected receipt image. */
  children: ReactNode;
  /** Shutter row for live capture; omit when previewing a selected photo. */
  controls?: CaptureControls;
  /** Bottom guidance, e.g. "Keep the date, total and all four edges visible." */
  footnote?: string;
}

const ControlLabel: React.FC<{ label: string; onPress?: () => void }> = ({ label, onPress }) => (
  <Pressable onPress={onPress} disabled={!onPress} accessibilityRole="button" hitSlop={12} style={styles.controlLabel}>
    <AppText variant="body12" color={colors.text.inverse} align="center">
      {label}
    </AppText>
  </Pressable>
);

/** Dark capture surface with a highlighted frame — receipt camera and photo selection. */
const CapturePanel: React.FC<CapturePanelProps> = ({ caption, captionIcon, children, controls, footnote }) => (
  <View style={styles.panel}>
    <View style={styles.captionRow}>
      {captionIcon ? <Icon name={captionIcon} size={18} color={colors.text.inverse} /> : null}
      <AppText variant="body12" color={colors.text.inverse}>
        {caption}
      </AppText>
    </View>
    <View style={styles.frame}>{children}</View>
    {footnote ? (
      <AppText variant="body12" color={colors.text.inverse}>
        {footnote}
      </AppText>
    ) : null}
    {controls ? (
      <View style={styles.controls}>
        <ControlLabel label={strings.common.capture.retake} onPress={controls.onRetake} />
        <ShutterButton onPress={controls.onCapture} />
        <ControlLabel label={controls.flashLabel ?? strings.common.capture.flashOff} onPress={controls.onToggleFlash} />
      </View>
    ) : null}
  </View>
);

const styles = StyleSheet.create({
  panel: {
    width: '100%',
    gap: 12,
    padding: 16,
    borderRadius: radii.xxl,
    backgroundColor: colors.surfaceInverse,
  },
  captionRow: { flexDirection: 'row', alignItems: 'center', gap: 8 },
  frame: {
    borderRadius: radii.sm,
    borderWidth: 2,
    borderColor: colors.primaryLight,
    padding: 4,
  },
  controls: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingTop: 4 },
  controlLabel: { width: 72 },
});

export default CapturePanel;
