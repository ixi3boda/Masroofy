import { useEffect, useRef, useState } from 'react';

/** Counts down from `seconds` to 0; call `restart()` (or `restart(n)`) to run it again (e.g. after a resend). */
export function useCountdown(seconds: number) {
  const [remaining, setRemaining] = useState(seconds);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const clear = () => {
    if (intervalRef.current) clearInterval(intervalRef.current);
  };

  const startInterval = () => {
    clear();
    intervalRef.current = setInterval(() => {
      setRemaining((prev) => {
        if (prev <= 1) {
          clear();
          return 0;
        }
        return prev - 1;
      });
    }, 1000);
  };

  useEffect(() => {
    startInterval();
    return clear;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Runs the countdown again, from `nextSeconds` when given (e.g. the server's cooldown), else from `seconds`. */
  const restart = (nextSeconds: number = seconds) => {
    setRemaining(nextSeconds);
    startInterval();
  };

  return { remaining, isDone: remaining <= 0, restart };
}
