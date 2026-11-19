import React, { ReactNode } from 'react';
import { View, TouchableOpacity, StyleSheet } from 'react-native';
import Text from '@/components/atoms/Text';
import Icon from '@/components/atoms/Icon';
import Divider from '@/components/atoms/Divider';

export interface ListItemProps {
  title: string;
  subtitle?: string;
  left?: ReactNode;
  right?: ReactNode;
  onPress?: () => void;
  showArrow?: boolean;
  disabled?: boolean;
}

const ListItem: React.FC<ListItemProps> = ({
  title,
  subtitle,
  left,
  right,
  onPress,
  showArrow = false,
  disabled = false,
}) => {
  return (
    <TouchableOpacity
      onPress={onPress}
      disabled={disabled || !onPress}
      activeOpacity={0.7}
      style={[styles.container, disabled && styles.disabled]}
    >
      <View style={styles.row}>
        {left && <View style={styles.leftContainer}>{left}</View>}
        <View style={styles.content}>
          <Text variant="subheading14" color="#242D35">{title}</Text>
          {subtitle && (
            <Text variant="body12" color="#6B7580" style={styles.subtitle}>
              {subtitle}
            </Text>
          )}
        </View>
        {right && <View style={styles.rightContainer}>{right}</View>}
        {showArrow && (
          <Icon name="chevron-right" size={20} color="#9BA1A8" style={styles.arrow} />
        )}
      </View>
      <Divider />
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  container: {
    width: '100%',
  },
  disabled: {
    opacity: 0.5,
  },
  row: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
    paddingHorizontal: 16,
  },
  leftContainer: {
    marginRight: 12,
  },
  content: {
    flex: 1,
  },
  subtitle: {
    marginTop: 2,
  },
  rightContainer: {
    marginLeft: 8,
  },
  arrow: {
    marginLeft: 4,
  },
});

export default ListItem;
