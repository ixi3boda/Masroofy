import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import {
  BadgeDollarSign,
  Bell,
  Bike,
  ChartColumn,
  ChevronLeft,
  CircleCheck,
  CircleUserRound,
  House,
  Info,
  Landmark,
  LockKeyhole,
  Mail,
  MailCheck,
  MessageSquareText,
  Mic,
  PiggyBank,
  Plus,
  Receipt,
  ScanLine,
  Settings,
  ShieldCheck,
  ShoppingCart,
  TrendingUp,
  TriangleAlert,
  Wallet,
  type LucideIcon,
} from 'lucide-react-native';
import { colors } from '@theme/index';

const ICONS = {
  wallet: Wallet,
  'chevron-left': ChevronLeft,
  mail: Mail,
  'mail-check': MailCheck,
  'lock-keyhole': LockKeyhole,
  'shield-check': ShieldCheck,
  info: Info,
  'circle-check': CircleCheck,
  'triangle-alert': TriangleAlert,
  user: CircleUserRound,
  bell: Bell,
  'piggy-bank': PiggyBank,
  'chart-column': ChartColumn,
  'trending-up': TrendingUp,
  landmark: Landmark,
  salary: BadgeDollarSign,
  plus: Plus,
  sms: MessageSquareText,
  scan: ScanLine,
  mic: Mic,
  home: House,
  settings: Settings,
  groceries: ShoppingCart,
  transport: Bike,
  bills: Receipt,
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof ICONS;

export interface IconProps {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
  /** Shows a small notification dot on the top-right corner. */
  dot?: boolean;
  style?: StyleProp<ViewStyle>;
}

const Icon: React.FC<IconProps> = ({
  name,
  size = 24,
  color = colors.text.primary,
  strokeWidth = 2,
  dot = false,
  style,
}) => {
  const LucideIcon = ICONS[name];

  if (!dot) {
    return <LucideIcon size={size} color={color} strokeWidth={strokeWidth} style={style} />;
  }

  const dotSize = Math.max(6, Math.round(size * 0.35));
  return (
    <View style={style}>
      <LucideIcon size={size} color={color} strokeWidth={strokeWidth} />
      <View
        style={[
          styles.dot,
          {
            width: dotSize,
            height: dotSize,
            borderRadius: dotSize / 2,
            top: -dotSize / 4,
            right: -dotSize / 4,
          },
        ]}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  dot: {
    position: 'absolute',
    backgroundColor: colors.notification,
    borderWidth: 1.5,
    borderColor: colors.surface,
  },
});

export default Icon;
