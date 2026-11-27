import { useCallback, useEffect, useRef } from 'react';

/** For async handlers that navigate: a screen the user already left must not move the one now showing. */
export const useIsMounted = () => {
  const mounted = useRef(false);

  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);

  return useCallback(() => mounted.current, []);
};
