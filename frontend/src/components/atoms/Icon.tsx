import React from 'react';
import { StyleProp, StyleSheet, View, ViewStyle } from 'react-native';
import {
  BadgeDollarSign,
  Bell,
  Bike,
  Building2,
  ChartColumn,
  Check,
  ChevronDown,
  ChevronLeft,
  CircleAlert,
  CircleCheck,
  CircleUserRound,
  Ellipsis,
  HeartPulse,
  House,
  Info,
  Landmark,
  Link,
  LockKeyhole,
  Mail,
  MailCheck,
  MessageSquareText,
  Mic,
  PiggyBank,
  Plus,
  Receipt,
  ScanLine,
  Search,
  SearchX,
  Settings,
  ShieldCheck,
  ShoppingBag,
  ShoppingCart,
  TrendingUp,
  TriangleAlert,
  Utensils,
  Wallet,
  ArrowLeftRight,
  Camera,
  CalendarCheck,
  ChevronRight,
  CloudOff,
  FileCheck,
  FileWarning,
  Globe,
  Laptop,
  MessageSquareWarning,
  Pencil,
  TrendingDown,
  WifiOff,
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
  rent: Building2,
  dining: Utensils,
  health: HeartPulse,
  shopping: ShoppingBag,
  other: Ellipsis,
  check: Check,
  'chevron-down': ChevronDown,
  'circle-alert': CircleAlert,
  search: Search,
  'search-x': SearchX,
  link: Link,
  pencil: Pencil,
  'chevron-right': ChevronRight,
  'trending-down': TrendingDown,
  'cloud-off': CloudOff,
  'wifi-off': WifiOff,
  'file-warning': FileWarning,
  'file-check': FileCheck,
  'calendar-check': CalendarCheck,
  'message-warning': MessageSquareWarning,
  laptop: Laptop,
  camera: Camera,
  transfer: ArrowLeftRight,
  globe: Globe,
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
    backgroundColor: colors.danger,
    borderWidth: 1.5,
    borderColor: colors.surface,
  },
});

export default Icon;
