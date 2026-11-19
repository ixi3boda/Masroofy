import React from 'react';
import { View, StyleSheet } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Text from '@/components/atoms/Text';

export interface BrandIdentityProps {
  size?: 'sm' | 'md' | 'lg';
}

const SIZE_MAP = {
  sm: { badge: 52, radius: 16, icon: 26, fontSize: 20 },
  md: { badge: 72, radius: 22, icon: 36, fontSize: 28 },
  lg: { badge: 96, radius: 28, icon: 48, fontSize: 36 },
};

const BrandIdentity: React.FC<BrandIdentityProps> = ({ size = 'md' }) => {
  const cfg = SIZE_MAP[size];

  return (
    <View style={styles.container}>
      <LinearGradient
        colors={['#2FDAFF', '#0E33F3']}
        start={{ x: 0.22, y: 0 }}
        end={{ x: 0.78, y: 1 }}
        style={[
          styles.badge,
          {
            width: cfg.badge,
            height: cfg.badge,
            borderRadius: cfg.radius,
          },
        ]}
      >
        {/* Wallet SVG placeholder rendered as a simple icon */}
        <View style={[styles.walletIcon, { width: cfg.icon, height: cfg.icon }]}>
          {/* Wallet body */}
          <View
            style={[
              styles.walletBody,
              {
                width: cfg.icon,
                height: cfg.icon * 0.65,
                borderRadius: cfg.icon * 0.12,
              },
            ]}
          />
          {/* Wallet flap */}
          <View
            style={[
              styles.walletFlap,
              {
                width: cfg.icon * 0.55,
                height: cfg.icon * 0.3,
                borderRadius: cfg.icon * 0.08,
                top: cfg.icon * 0.08,
                right: cfg.icon * 0.1,
              },
            ]}
          />
        </View>
      </LinearGradient>

      <Text variant="h1" color="#242D35" align="center" style={styles.brandName}>
        Masroofy
      </Text>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    justifyContent: 'center',
  },
  badge: {
    alignItems: 'center',
    justifyContent: 'center',
    overflow: 'hidden',
  },
  walletIcon: {
    alignItems: 'center',
    justifyContent: 'center',
    position: 'relative',
  },
  walletBody: {
    backgroundColor: 'rgba(255,255,255,0.9)',
    position: 'absolute',
  },
  walletFlap: {
    backgroundColor: 'rgba(255,255,255,0.7)',
    position: 'absolute',
  },
  brandName: {
    marginTop: 16,
  },
});

export default BrandIdentity;
