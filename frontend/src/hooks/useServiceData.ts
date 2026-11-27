import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';

/** Service reads are plain JSON data, so equal text means nothing changed. */
const isSame = (a: unknown, b: unknown) => a === b || JSON.stringify(a) === JSON.stringify(b);

/**
 * A synchronous service read that is repeated whenever the screen is shown again,
 * because screens pushed on top may have changed it. `read` must be stable.
 * Unchanged data keeps its old reference, so opening or returning to a screen
 * re-renders it only when something actually changed.
 */
export const useServiceData = <T>(read: () => T): T => {
  const [data, setData] = useState(read);
  useFocusEffect(
    useCallback(() => {
      setData((current) => {
        const next = read();
        return isSame(current, next) ? current : next;
      });
    }, [read]),
  );
  return data;
};
