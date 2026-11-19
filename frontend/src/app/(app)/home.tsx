import { router } from 'expo-router';
import { StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { colors, spacing } from '@theme/index';
import AppText from '@components/atoms/Text';
import Button from '@components/atoms/Button';

/**
 * Temporary landing stub so the "01" auth flow has somewhere real to go once
 * sign-up/login succeeds. Replace with the actual home screen once it's built.
 */
export default function HomeStub() {
  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.content}>
        <AppText variant="h1">You&rsquo;re in</AppText>
        <AppText variant="body14" color={colors.text.secondary} align="center">
          This is a placeholder landing screen for testing the auth flow. The real home
          screen is not built yet.
        </AppText>
        <Button title="Back to welcome" variant="outline" onPress={() => router.replace('/(auth)/welcome')} />
      </View>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: colors.background },
  content: {
    flex: 1,
    alignItems: 'center',
    justifyContent: 'center',
    gap: spacing.lg,
    paddingHorizontal: spacing.xxl,
  },
});
