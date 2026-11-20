import React, { memo } from 'react';
import { Pressable, StyleSheet } from 'react-native';
import { radii } from '@theme/index';
import AppText from '@components/atoms/Text';
import Card from '@components/atoms/Card';
import Icon from '@components/atoms/Icon';

export interface RecentSearchItemProps {
  query: string;
  onPress?: () => void;
}

const RecentSearchItem: React.FC<RecentSearchItemProps> = ({ query, onPress }) => (
  <Pressable
    onPress={onPress}
    disabled={!onPress}
    accessibilityRole="button"
    accessibilityLabel={`Search for ${query}`}
    style={({ pressed }) => pressed && styles.pressed}
  >
    <Card style={styles.card}>
      <Icon name="search" />
      <AppText variant="body14" numberOfLines={1} style={styles.query}>
        {query}
      </AppText>
    </Card>
  </Pressable>
);

const styles = StyleSheet.create({
  pressed: { opacity: 0.8 },
  card: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 12,
    paddingHorizontal: 12,
    paddingVertical: 12,
    borderRadius: radii.md,
  },
  query: { flex: 1 },
});

export default memo(RecentSearchItem);
