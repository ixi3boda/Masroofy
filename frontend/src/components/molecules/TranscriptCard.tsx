import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Icon from '@components/atoms/Icon';
import Input from '@components/atoms/Input';

export interface TranscriptCardProps {
  transcript: string;
  /** When set, the transcript becomes an editable field. */
  onChangeTranscript?: (text: string) => void;
  caption?: string;
}

/** Voice-entry transcript, shown read-only or as an editable field for corrections. */
const TranscriptCard: React.FC<TranscriptCardProps> = ({ transcript, onChangeTranscript, caption }) => (
  <Card style={styles.card}>
    <View style={styles.heading}>
      <Icon name="pencil" size={20} color={colors.primary} />
      <AppText variant="subheading14">Editable transcript</AppText>
    </View>
    {onChangeTranscript ? (
      <Input label="Transcript words" value={transcript} onChangeText={onChangeTranscript} />
    ) : (
      <AppText variant="subheading18">{transcript}</AppText>
    )}
    {caption ? (
      <AppText variant="body12" color={colors.text.secondary}>
        {caption}
      </AppText>
    ) : null}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 12 },
  heading: { flexDirection: 'row', alignItems: 'center', gap: 8 },
});

export default TranscriptCard;
