import React from 'react';
import { StyleSheet, View } from 'react-native';
import { colors } from '@theme/index';
import AppText from '@components/atoms/Text';
import Avatar from '@components/atoms/Avatar';
import Button from '@components/atoms/Button';
import Card from '@components/atoms/Card';
import { strings } from '@/strings';

export interface ProfileSummaryProps {
  name: string;
  /** e.g. "Cairo, Egypt" */
  location?: string;
  onEdit?: () => void;
}

const ProfileSummary: React.FC<ProfileSummaryProps> = ({ name, location, onEdit }) => (
  <Card style={styles.card}>
    <View style={styles.row}>
      <Avatar name={name} />
      <View style={styles.copy}>
        <AppText variant="subheading18">{name}</AppText>
        {location ? (
          <AppText variant="body12" color={colors.text.secondary}>
            {location}
          </AppText>
        ) : null}
      </View>
    </View>
    {onEdit ? <Button title={strings.common.linkArrow(strings.common.profile.edit)} variant="link" size="sm" onPress={onEdit} style={styles.edit} /> : null}
  </Card>
);

const styles = StyleSheet.create({
  card: { gap: 8 },
  row: { flexDirection: 'row', alignItems: 'center', gap: 12 },
  copy: { flex: 1, gap: 2 },
  edit: { paddingHorizontal: 0, height: 32 },
});

export default ProfileSummary;
