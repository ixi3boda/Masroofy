import { Stack } from 'expo-router';

export default function AuthLayout() {
  return (
    <Stack screenOptions={{ headerShown: false }}>
      {/* iOS swipe-back would bypass the screen's "back to login" handling. */}
      <Stack.Screen name="password-updated" options={{ gestureEnabled: false }} />
    </Stack>
  );
}
