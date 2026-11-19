import React, { useState } from 'react';
import { View, StyleSheet } from 'react-native';
import FormField from '@/components/molecules/FormField';
import Button from '@/components/atoms/Button';
import Text from '@/components/atoms/Text';

export interface SignUpFormProps {
  onSubmit: (data: { name: string; email: string; password: string }) => void;
  loading?: boolean;
  error?: string;
}

const SignUpForm: React.FC<SignUpFormProps> = ({ onSubmit, loading = false, error }) => {
  const [name, setName] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSubmit = () => {
    onSubmit({ name, email, password });
  };

  return (
    <View style={styles.container}>
      <FormField
        label="Full Name"
        placeholder="Enter your name"
        value={name}
        onChangeText={setName}
        autoCapitalize="words"
      />

      <View style={styles.fieldGap} />

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
        placeholder="Create a password"
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
        title="Create Account"
        variant="primary"
        size="lg"
        onPress={handleSubmit}
        loading={loading}
        disabled={loading}
        fullWidth
        style={styles.button}
      />

      <Text variant="body12" color="#6B7580" align="center" style={styles.terms}>
        By creating an account, you agree to our Terms of Service and Privacy Policy.
      </Text>
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
  terms: {
    marginTop: 16,
  },
});

export default SignUpForm;
