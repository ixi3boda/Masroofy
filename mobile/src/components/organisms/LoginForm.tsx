import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import FormField from '@/components/molecules/FormField';
import Button from '@/components/atoms/Button';
import Text from '@/components/atoms/Text';

export interface LoginFormProps {
  onSubmit: (data: { email: string; password: string }) => void;
  loading?: boolean;
  error?: string;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSubmit, loading = false, error }) => {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = () => {
    onSubmit({ email, password });
  };

  return (
    <View style={styles.container}>
      <FormField
        label="Email"
        placeholder="Enter your email"
        value={email}
        onChangeText={setEmail}
        keyboardType="email-address"
        autoCapitalize="none"
      />

      <View style={styles.fieldGap} />

      <FormField
        label="Password"
        placeholder="Enter your password"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoCapitalize="none"
      />

      {error ? (
        <Text variant="body12" color="#EF4E4E" style={styles.errorText}>
          {error}
        </Text>
      ) : null}

      <Button
        title="Sign In"
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
  container: {
    width: '100%',
  },
  fieldGap: {
    height: 16,
  },
  errorText: {
    marginTop: 8,
  },
  button: {
    marginTop: 24,
  },
});

export default LoginForm;
