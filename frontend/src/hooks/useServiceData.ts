import { useCallback, useState } from 'react';
import { useFocusEffect } from 'expo-router';

/**
 * A synchronous service read that is repeated whenever the screen is shown again,
 * because screens pushed on top may have changed it. `read` must be stable.
 */
export const useServiceData = <T>(read: () => T): T => {
  const [data, setData] = useState(read);
  useFocusEffect(useCallback(() => setData(() => read()), [read]));
  return data;
};
