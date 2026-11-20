import { UserProfile } from '@/types/auth';
import { ApiError, isApiError } from '@/utils/errors';
import { request, RequestOptions } from './client';
import { refreshTokens } from './endpoints/token';
import { tokenStorage } from './tokenStorage';
import { TokenResponse } from './types';

/**
 * Token rules from docs/frontend-api/00 §6: access token in memory, refresh
 * token in secure storage, refresh before it expires, one refresh at a time
 * shared by every caller, and on 401 refresh once then retry once.
 */

/** Refresh this long before the access token expires. */
const EXPIRY_MARGIN_MS = 60_000;
/** Refresh failures that mean the session is over (tokens are cleared). Others (offline, 503) keep them. */
const SESSION_OVER_CODES = new Set(['INVALID_REFRESH_TOKEN', 'ACCOUNT_DISABLED', 'EMAIL_NOT_VERIFIED', 'VALIDATION_FAILED']);

let accessToken: string | null = null;
let accessTokenExpiresAt = 0;
let refreshInFlight: Promise<UserProfile> | null = null;
let onSessionEnded: () => void = () => {};

/** Called when the session ends by itself (refresh rejected): the app goes to Login. */
export const setSessionEndedHandler = (handler: () => void) => {
  onSessionEnded = handler;
};

export const isSessionOverError = (error: unknown) => isApiError(error) && SESSION_OVER_CODES.has(error.code);

export async function saveTokens({ accessToken: token, refreshToken, expiresIn }: TokenResponse): Promise<void> {
  accessToken = token;
  accessTokenExpiresAt = Date.now() + expiresIn * 1000;
  await tokenStorage.setRefreshToken(refreshToken);
}

export async function clearSession(): Promise<void> {
  accessToken = null;
  accessTokenExpiresAt = 0;
  await tokenStorage.clear();
}

export const hasStoredSession = async () => (await tokenStorage.getRefreshToken()) !== null;

const endSession = async () => {
  await clearSession();
  onSessionEnded();
};

async function runRefresh(): Promise<UserProfile> {
  const refreshToken = await tokenStorage.getRefreshToken();
  if (!refreshToken) throw new ApiError('INVALID_REFRESH_TOKEN', 401, 'No stored session');
  try {
    const tokens = await refreshTokens(refreshToken);
    await saveTokens(tokens);
    return tokens.user;
  } catch (error) {
    if (isSessionOverError(error)) await endSession();
    throw error;
  }
}

/** Swaps the stored refresh token for new tokens. Parallel callers share one request. */
export function refreshSession(): Promise<UserProfile> {
  refreshInFlight ??= runRefresh().finally(() => {
    refreshInFlight = null;
  });
  return refreshInFlight;
}

const isUnauthorized = (error: unknown) => isApiError(error, 'UNAUTHORIZED');

/** A protected call: refreshes first when needed, and once more after a `401`. */
export async function authorizedRequest<T>(path: string, options: Omit<RequestOptions, 'token'> = {}): Promise<T> {
  if (!accessToken || Date.now() >= accessTokenExpiresAt - EXPIRY_MARGIN_MS) await refreshSession();
  try {
    return await request<T>(path, { ...options, token: accessToken ?? undefined });
  } catch (error) {
    if (!isUnauthorized(error)) throw error;
  }
  await refreshSession();
  try {
    return await request<T>(path, { ...options, token: accessToken ?? undefined });
  } catch (error) {
    if (isUnauthorized(error)) await endSession();
    throw error;
  }
}
