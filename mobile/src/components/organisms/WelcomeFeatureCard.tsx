import React from 'react';
import { View, StyleSheet } from 'react-native';
import Text from '@/components/atoms/Text';
import Divider from '@/components/atoms/Divider';

export interface WelcomeFeatureCardProps {
  title: string;
  features: string[];
}

const WelcomeFeatureCard: React.FC<WelcomeFeatureCardProps> = ({ title, features }) => {
  return (
    <View style={styles.card}>
      <Text variant="subheading16" color="#242D35" style={styles.title}>
        {title}
      </Text>

      {features.map((feature, index) => (
        <View key={index}>
          {index > 0 && <Divider style={styles.divider} />}
          <View style={styles.featureRow}>
            {/* Bullet dot */}
            <View style={styles.bullet} />
            <Text variant="body14" color="#242D35" style={styles.featureText}>
              {feature}
            </Text>
          </View>
        </View>
      ))}
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 20,
    shadowColor: '#1D3A58',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 32,
    elevation: 8,
    width: '100%',
  },
  title: {
    marginBottom: 16,
  },
  divider: {
    marginVertical: 0,
  },
  featureRow: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingVertical: 12,
  },
  bullet: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: '#0E33F3',
    marginRight: 12,
    flexShrink: 0,
  },
  featureText: {
    flex: 1,
  },
});

export default WelcomeFeatureCard;
