import { Platform } from 'react-native';
import * as SecureStore from 'expo-secure-store';

/**
 * Where the refresh token lives: the OS keychain / keystore through
 * `expo-secure-store`. That module does not exist on web, so on web the token
 * stays in memory only (a page reload means logging in again). Never use
 * AsyncStorage or plain files for it. The access token is not stored here: it
 * stays in memory in `session.ts`.
 */

const REFRESH_TOKEN_KEY = 'masroofy.refreshToken';
const useSecureStore = Platform.OS !== 'web';
let memoryRefreshToken: string | null = null;

export const tokenStorage = {
  async getRefreshToken(): Promise<string | null> {
    if (!useSecureStore) return memoryRefreshToken;
    try {
      return await SecureStore.getItemAsync(REFRESH_TOKEN_KEY);
    } catch {
      return null;
    }
  },

  async setRefreshToken(token: string): Promise<void> {
    if (!useSecureStore) {
      memoryRefreshToken = token;
      return;
    }
    await SecureStore.setItemAsync(REFRESH_TOKEN_KEY, token);
  },

  async clear(): Promise<void> {
    memoryRefreshToken = null;
    if (!useSecureStore) return;
    try {
      await SecureStore.deleteItemAsync(REFRESH_TOKEN_KEY);
    } catch {
      // Nothing stored, or the keystore is unavailable: either way there is no token left to use.
    }
  },
};
