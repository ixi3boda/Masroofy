import React from 'react';
import { View, StyleSheet } from 'react-native';
import Input, { InputProps } from '@/components/atoms/Input';
import Text from '@/components/atoms/Text';

export interface FormFieldProps extends InputProps {
  label: string;
  error?: string;
  hint?: string;
}

const FormField: React.FC<FormFieldProps> = ({ label, error, hint, ...inputProps }) => {
  return (
    <View style={styles.container}>
      <Text variant="subheading12" color="#242D35" style={styles.label}>
        {label}
      </Text>
      <Input {...inputProps} hasError={!!error} errorMessage={error} hint={hint} />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flexDirection: 'column',
    width: '100%',
  },
  label: {
    marginBottom: 6,
  },
});

export default FormField;
