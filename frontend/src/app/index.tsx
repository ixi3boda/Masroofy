import { Redirect } from 'expo-router';
import { useSessionStore } from '@/store/sessionStore';

export default function Index() {
  const isSignedIn = useSessionStore((state) => state.user !== null);
  return <Redirect href={isSignedIn ? '/(app)/home' : '/(auth)/welcome'} />;
}
