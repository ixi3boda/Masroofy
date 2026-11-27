import React, { useCallback, useEffect, useState } from 'react';
import { Redirect } from 'expo-router';
import Button from '@components/atoms/Button';
import InlineLoader from '@components/molecules/InlineLoader';
import StateSummary from '@components/molecules/StateSummary';
import ScreenLayout from '@components/templates/ScreenLayout';
import { ROUTES } from '@/navigation/routes';
import { authService } from '@/services/authService';
import { useSessionStore } from '@/store/sessionStore';
import { strings } from '@/strings';

const copy = strings.auth.startup;

/**
 * App entry. Checks once for a stored session (refresh at app start), then
 * sends the user Home or to Welcome. Offline or server down: the stored
 * session is kept and the user can retry.
 */
const StartupScreen: React.FC = () => {
  const isSignedIn = useSessionStore((state) => state.user !== null);
  const sessionChecked = useSessionStore((state) => state.sessionChecked);
  const signIn = useSessionStore((state) => state.signIn);
  const finishSessionCheck = useSessionStore((state) => state.finishSessionCheck);
  const [failed, setFailed] = useState(false);

  const checkSession = useCallback(
    () =>
      authService.restoreSession().then(
        (user) => {
          if (user) signIn(user);
          finishSessionCheck();
        },
        () => setFailed(true)
      ),
    [signIn, finishSessionCheck]
  );

  useEffect(() => {
    if (!sessionChecked) checkSession();
  }, [sessionChecked, checkSession]);

  const retry = () => {
    setFailed(false);
    checkSession();
  };

  if (sessionChecked) return <Redirect href={isSignedIn ? ROUTES.app.home : ROUTES.auth.welcome} />;

  return (
    <ScreenLayout footer={failed ? <Button title={copy.retry} onPress={retry} /> : undefined}>
      {failed ? (
        <StateSummary icon="wifi-off" heading={copy.offlineHeading} description={copy.offlineDescription} />
      ) : (
        <InlineLoader label={copy.checking} />
      )}
    </ScreenLayout>
  );
};

export default StartupScreen;
