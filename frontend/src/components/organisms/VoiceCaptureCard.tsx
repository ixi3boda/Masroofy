import React from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Chip from '@components/atoms/Chip';
import Icon from '@components/atoms/Icon';
import IconBadge from '@components/atoms/IconBadge';
import Waveform from '@components/atoms/Waveform';
import { strings } from '@/strings';

export interface VoiceCaptureCardProps {
  recording: boolean;
  /** Start/stop recording. */
  onToggleRecording?: () => void;
  /** Idle heading, e.g. "Ready when you are". */
  title?: string;
  /** e.g. "Recording · 00:06" — shown while recording. */
  status?: string;
  /** Recent microphone levels (0–1) for the live waveform. */
  levels?: number[];
  /** Live or example transcript line. */
  transcript?: string;
  caption?: string;
}

/** Microphone panel for voice entry — idle prompt or live recording with waveform. */
const VoiceCaptureCard: React.FC<VoiceCaptureCardProps> = ({
  recording,
  onToggleRecording,
  title,
  status,
  levels,
  transcript,
  caption,
}) => (
  <Card style={styles.card}>
    {recording && status ? <Chip label={status} style={styles.centered} /> : null}
    <Pressable
      onPress={onToggleRecording}
      disabled={!onToggleRecording}
      accessibilityRole="button"
      accessibilityLabel={recording ? strings.common.a11y.stopRecording : strings.common.a11y.startRecording}
      accessibilityState={{ busy: recording }}
    >
      <IconBadge size="lg">
        <Icon name="mic" size={36} color={colors.text.inverse} />
      </IconBadge>
    </Pressable>
    {!recording && title ? (
      <AppText variant="h2" align="center">
        {title}
      </AppText>
    ) : null}
    {recording && levels?.length ? <Waveform levels={levels} /> : null}
    {transcript ? (
      <AppText variant="body14" align="center" accessibilityLiveRegion="polite">
        {transcript}
      </AppText>
    ) : null}
    {caption ? (
      <AppText variant="body12" color={colors.text.secondary} align="center">
        {caption}
      </AppText>
    ) : null}
  </Card>
);

const styles = StyleSheet.create({
  card: { alignItems: 'center', gap: 16, paddingVertical: 24 },
  centered: { alignSelf: 'center' },
});

export default VoiceCaptureCard;
