import { API_TIMEOUT_MS, API_URL } from '@/config/env';
import { ApiError } from '@/utils/errors';
import { ApiErrorBody } from './types';

export interface RequestOptions {
  method?: 'GET' | 'POST';
  body?: unknown;
  /** Access token for protected endpoints. */
  token?: string;
}

const NOT_JSON = Symbol('not-json');

const parseJson = (text: string): unknown => {
  if (!text) return undefined;
  try {
    return JSON.parse(text);
  } catch {
    return NOT_JSON;
  }
};

const toApiError = (status: number, data: unknown): ApiError => {
  const body = (data && typeof data === 'object' ? data : {}) as ApiErrorBody;
  const code = body.code ?? (status >= 500 ? 'INTERNAL_ERROR' : 'INVALID_RESPONSE');
  return new ApiError(code, status, body.message ?? `HTTP ${status}`, body.fieldErrors ?? [], body.details ?? {});
};

/**
 * One call to the backend: JSON in and out, Bearer header, timeout. Every
 * failure (server error body, no network, timeout, non-JSON answer) becomes an
 * `ApiError`. A `204` resolves to `undefined`. Never logs bodies or tokens.
 */
export async function request<T>(path: string, { method = 'POST', body, token }: RequestOptions = {}): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), API_TIMEOUT_MS);
  const headers: Record<string, string> = { Accept: 'application/json' };
  if (body !== undefined) headers['Content-Type'] = 'application/json';
  if (token) headers.Authorization = `Bearer ${token}`;

  let status: number;
  let data: unknown;
  try {
    const response = await fetch(`${API_URL}${path}`, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
      signal: controller.signal,
    });
    status = response.status;
    data = status === 204 ? undefined : parseJson(await response.text());
  } catch {
    throw controller.signal.aborted
      ? new ApiError('TIMEOUT', 0, `No answer within ${API_TIMEOUT_MS} ms`)
      : new ApiError('NETWORK_ERROR', 0, `Could not reach ${API_URL}`);
  } finally {
    clearTimeout(timer);
  }

  if (status < 200 || status >= 300) throw toApiError(status, data === NOT_JSON ? undefined : data);
  if (data === NOT_JSON) throw new ApiError('INVALID_RESPONSE', status, 'The answer was not JSON');
  return data as T;
}
