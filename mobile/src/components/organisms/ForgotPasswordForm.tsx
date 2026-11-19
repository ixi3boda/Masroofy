import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import FormField from '@/components/molecules/FormField';
import Button from '@/components/atoms/Button';
import Text from '@/components/atoms/Text';

export interface ForgotPasswordFormProps {
  onSubmit: (email: string) => void;
  loading?: boolean;
}

const ForgotPasswordForm: React.FC<ForgotPasswordFormProps> = ({
  onSubmit,
  loading = false,
}) => {
  const [email, setEmail] = useState('');

  const handleSubmit = () => {
    onSubmit(email);
  };

  return (
    <View style={styles.card}>
      <Text variant="body12" color="#6B7580" style={styles.hint}>
        Enter the email address associated with your account and we'll send you a link to reset your password.
      </Text>

      <FormField
        label="Email"
        placeholder="Enter your email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
        style={styles.fieldGap}
      />

      <Button
        title="Request Reset Link"
        variant="primary"
        size="lg"
        onPress={handleSubmit}
        loading={loading}
        disabled={loading}
        fullWidth
        style={styles.button}
      />
    </View>
  );
};

const styles = StyleSheet.create({
  card: {
    backgroundColor: '#FFFFFF',
    borderRadius: 24,
    padding: 24,
    shadowColor: '#1D3A58',
    shadowOffset: { width: 0, height: 8 },
    shadowOpacity: 0.12,
    shadowRadius: 32,
    elevation: 8,
    width: '100%',
  },
  hint: {
    marginBottom: 20,
    lineHeight: 18,
  },
  fieldGap: {
    marginBottom: 0,
  },
  button: {
    marginTop: 24,
  },
});

export default ForgotPasswordForm;
