import { Redirect } from 'expo-router';
import { ROUTES } from '@/navigation/routes';
import { useSessionStore } from '@/store/sessionStore';

export default function Index() {
  const isSignedIn = useSessionStore((state) => state.user !== null);
  return <Redirect href={isSignedIn ? ROUTES.app.home : ROUTES.auth.welcome} />;
}
