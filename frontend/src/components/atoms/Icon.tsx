import React from 'react';
import { StyleProp, ViewStyle } from 'react-native';
import {
  ChevronLeft,
  CircleCheck,
  Info,
  LockKeyhole,
  Mail,
  MailCheck,
  ShieldCheck,
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
} satisfies Record<string, LucideIcon>;

export type IconName = keyof typeof ICONS;

export interface IconProps {
  name: IconName;
  size?: number;
  color?: string;
  strokeWidth?: number;
  style?: StyleProp<ViewStyle>;
}

const Icon: React.FC<IconProps> = ({ name, size = 24, color = colors.text.primary, strokeWidth = 2, style }) => {
  const LucideIcon = ICONS[name];
  return <LucideIcon size={size} color={color} strokeWidth={strokeWidth} style={style} />;
};

export default Icon;
