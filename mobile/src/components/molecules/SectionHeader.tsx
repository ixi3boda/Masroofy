import React from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
import Text from '@/components/atoms/Text';

export interface SectionHeaderProps {
  title: string;
  actionLabel?: string;
  onAction?: () => void;
}

const SectionHeader: React.FC<SectionHeaderProps> = ({ title, actionLabel, onAction }) => {
  return (
    <View style={styles.container}>
      <Text variant="subheading16" color="#242D35">{title}</Text>
      {actionLabel && (
        <TouchableOpacity onPress={onAction} activeOpacity={0.7}>
          <Text variant="body14" color="#0E33F3">{actionLabel}</Text>
        </TouchableOpacity>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    width: '100%',
  },
});

export default SectionHeader;
