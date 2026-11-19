import React from 'react';
import { View, StyleSheet } from 'react-native';
import Text from '@/components/atoms/Text';
import Divider from '@/components/atoms/Divider';

export interface FeatureListItemProps {
  label: string;
  showDivider?: boolean;
}

const FeatureListItem: React.FC<FeatureListItemProps> = ({ label, showDivider = true }) => {
  return (
    <View style={styles.container}>
      <Text variant="subheading14" color="#242D35" style={styles.label}>
        {label}
      </Text>
      {showDivider && <Divider />}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  label: {
    paddingVertical: 12,
  },
});

export default FeatureListItem;
