import { useState } from 'react';
import { CodeDelivery } from '@/types/auth';
import { isApiError } from '@/utils/errors';
import { useCountdown } from './useCountdown';

/**
 * "Resend code" button logic for the code screens: a countdown that starts at
 * `initialSeconds` and restarts with the server's cooldown after each send.
 * `RESEND_COOLDOWN` is not an error for the user: it just restarts the timer.
 * `resend()` resolves `true` when a new code was sent; other failures throw.
 */
export function useResendCode(send: () => Promise<CodeDelivery>, initialSeconds: number) {
  const { remaining, isDone, restart } = useCountdown(initialSeconds);
  const [resending, setResending] = useState(false);

  const resend = async (): Promise<boolean> => {
    setResending(true);
    try {
      const { resendAvailableInSeconds } = await send();
      restart(resendAvailableInSeconds);
      return true;
    } catch (error) {
      if (isApiError(error, 'RESEND_COOLDOWN') && error.details.retryAfterSeconds !== undefined) {
        restart(error.details.retryAfterSeconds);
        return false;
      }
      throw error;
    } finally {
      setResending(false);
    }
  };

  return { remaining, isDone, resending, resend };
}
