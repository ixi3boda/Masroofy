import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import OTPInput from '@/components/atoms/OTPInput';
import Button from '@/components/atoms/Button';
import Text from '@/components/atoms/Text';

export interface OTPVerificationProps {
  length?: number;
  onComplete: (otp: string) => void;
  onResend?: () => void;
  loading?: boolean;
  error?: string;
}

const OTPVerification: React.FC<OTPVerificationProps> = ({
  length = 6,
  onComplete,
  onResend,
  loading = false,
  error,
}) => {
  const [otp, setOtp] = useState('');

  const handleChange = (val: string) => {
    setOtp(val);
    if (val.length === length) {
      onComplete(val);
    }
  };

  return (
    <View style={styles.container}>
      <OTPInput
        length={length}
        value={otp}
        onChange={handleChange}
        hasError={!!error}
      />

      {error ? (
        <Text variant="body12" color="#EF4E4E" align="center" style={styles.error}>
          {error}
        </Text>
      ) : null}

      {onResend && (
        <Button
          title="Resend code"
          variant="ghost"
          size="md"
          onPress={onResend}
          disabled={loading}
          style={styles.resendBtn}
        />
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    alignItems: 'center',
    width: '100%',
  },
  error: {
    marginTop: 12,
  },
  resendBtn: {
    marginTop: 16,
  },
});

export default OTPVerification;
