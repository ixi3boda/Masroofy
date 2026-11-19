import React, { ReactNode } from 'react';
import { View, StyleSheet, StyleProp, ViewStyle } from 'react-native';
import Text from '@/components/atoms/Text';

export type InfoCardVariant = 'info' | 'warning' | 'error';

export interface InfoCardProps {
  title: string;
  description?: string;
  icon?: ReactNode;
  variant?: InfoCardVariant;
  style?: StyleProp<ViewStyle>;
}

const variantConfig: Record<
  InfoCardVariant,
  { stripeColor: string; bgColor: string }
> = {
  info: { stripeColor: '#0E33F3', bgColor: '#EEF1FE' },
  warning: { stripeColor: '#F59E0B', bgColor: '#FFFBEB' },
  error: { stripeColor: '#EF4E4E', bgColor: '#FEF2F2' },
};

const InfoCard: React.FC<InfoCardProps> = ({
  title,
  description,
  icon,
  variant = 'info',
  style,
}) => {
  const config = variantConfig[variant];

  return (
    <View style={[styles.card, { backgroundColor: config.bgColor }, style]}>
      <View style={[styles.stripe, { backgroundColor: config.stripeColor }]} />
      <View style={styles.body}>
        {icon && <View style={styles.icon}>{icon}</View>}
        <View style={styles.textContainer}>
          <Text variant="subheading14" color="#242D35">{title}</Text>
          {description && (
            <Text variant="body12" color="#6B7580" style={styles.description}>
              {description}
            </Text>
          )}
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    flexDirection: 'row',
    borderRadius: 16,
    overflow: 'hidden',
  },
  stripe: {
    width: 4,
    alignSelf: 'stretch',
  },
  body: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'flex-start',
    padding: 12,
  },
  icon: {
    marginRight: 10,
    marginTop: 2,
  },
  textContainer: {
    flex: 1,
  },
  description: {
    marginTop: 4,
  },
});

export default InfoCard;
