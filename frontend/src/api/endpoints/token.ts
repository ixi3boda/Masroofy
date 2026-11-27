import { request } from '../client';
import { TokenResponse } from '../types';

/**
 * API 5 — `POST /auth/token/refresh`, `200` (docs/frontend-api/05-refresh-token.md).
 * Swaps the stored refresh token for a new access token and a new refresh token.
 * Screens never call it: `api/session.ts` does (app start, before expiry, once after a `401`),
 * one refresh at a time. It lives apart from `auth.ts` because `auth.ts` imports `session.ts`.
 */
export const refreshTokens = (refreshToken: string) =>
  request<TokenResponse>('/auth/token/refresh', { body: { refreshToken } });
