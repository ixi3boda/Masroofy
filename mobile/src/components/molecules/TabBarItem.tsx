import React, { ReactNode } from 'react';
import { TouchableOpacity, View, StyleSheet } from 'react-native';
import Text from '@/components/atoms/Text';

export interface TabBarItemProps {
  icon: ReactNode;
  label: string;
  active?: boolean;
  onPress?: () => void;
}

const TabBarItem: React.FC<TabBarItemProps> = ({ icon, label, active = false, onPress }) => {
  const color = active ? '#0E33F3' : '#536171';

  return (
    <TouchableOpacity onPress={onPress} activeOpacity={0.7} style={styles.container}>
      <View style={styles.iconWrapper}>{icon}</View>
      <Text variant="caption10" color={color} align="center">
        {label}
      </Text>
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
    width: 24 + 16 * 2,
  },
  iconWrapper: {
    width: 24,
    height: 24,
    alignItems: 'center',
    justifyContent: 'center',
    marginBottom: 4,
  },
});

export default TabBarItem;
