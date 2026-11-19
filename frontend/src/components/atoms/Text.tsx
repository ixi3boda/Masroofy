import React from 'react';
import { Text as RNText, TextProps as RNTextProps, TextStyle } from 'react-native';
import { colors, typography, TypographyVariant } from '@theme/index';

export interface AppTextProps extends RNTextProps {
  variant?: TypographyVariant;
  color?: string;
  align?: TextStyle['textAlign'];
  children?: React.ReactNode;
}

const AppText: React.FC<AppTextProps> = ({
  variant = 'body14',
  color = colors.text.primary,
  align,
  style,
  children,
  ...rest
}) => {
  return (
    <RNText
      style={[typography[variant], { color }, align ? { textAlign: align } : undefined, style]}
      {...rest}
    >
      {children}
    </RNText>
  );
};

export default AppText;
