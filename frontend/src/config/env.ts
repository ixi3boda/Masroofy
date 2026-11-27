/**
 * The only place that reads `process.env`. Expo inlines `EXPO_PUBLIC_*` values
 * at bundle time, so each one is read by its literal name and changes need
 * `npx expo start -c`. Values come from `frontend/.env.local` (template:
 * `frontend/.env.example`). With nothing set, every service runs on its mock.
 */

export type DataSource = 'mock' | 'api';
export type ServiceName = 'auth' | 'dashboard' | 'sms' | 'transactions';

/** Services that have a backend API today. `api` for any other one falls back to `mock`. */
const HAS_API: Record<ServiceName, boolean> = {
  auth: true,
  dashboard: true,
  sms: false,
  transactions: false,
};

const warn = (message: string) => {
  if (__DEV__) console.warn(`[config] ${message}`);
};

const parseSource = (name: string, value: string | undefined): DataSource | undefined => {
  if (!value?.trim()) return undefined;
  const normalized = value.trim().toLowerCase();
  if (normalized === 'mock' || normalized === 'api') return normalized;
  warn(`${name}="${value}" is not "mock" or "api"; using "mock".`);
  return 'mock';
};

const API_MODE = parseSource('EXPO_PUBLIC_API_MODE', process.env.EXPO_PUBLIC_API_MODE) ?? 'mock';

const requested: Record<ServiceName, DataSource> = {
  auth: parseSource('EXPO_PUBLIC_AUTH_SOURCE', process.env.EXPO_PUBLIC_AUTH_SOURCE) ?? API_MODE,
  dashboard: parseSource('EXPO_PUBLIC_DASHBOARD_SOURCE', process.env.EXPO_PUBLIC_DASHBOARD_SOURCE) ?? API_MODE,
  sms: parseSource('EXPO_PUBLIC_SMS_SOURCE', process.env.EXPO_PUBLIC_SMS_SOURCE) ?? API_MODE,
  transactions:
    parseSource('EXPO_PUBLIC_TRANSACTIONS_SOURCE', process.env.EXPO_PUBLIC_TRANSACTIONS_SOURCE) ?? API_MODE,
};

const resolveSource = (service: ServiceName): DataSource => {
  if (requested[service] === 'api' && !HAS_API[service]) {
    warn(`the backend has no ${service} API yet; ${service} uses "mock".`);
    return 'mock';
  }
  return requested[service];
};

const SOURCES: Record<ServiceName, DataSource> = {
  auth: resolveSource('auth'),
  dashboard: resolveSource('dashboard'),
  sms: resolveSource('sms'),
  transactions: resolveSource('transactions'),
};

/** Where a service gets its data: its in-memory mock or the real backend. */
export const getDataSource = (service: ServiceName): DataSource => SOURCES[service];

/** True when `service` runs on its mock (screens use this only for mock-only QA hints). */
export const isMockSource = (service: ServiceName): boolean => SOURCES[service] === 'mock';

/** Backend base URL, without a trailing slash, e.g. `http://localhost:8080/api/v1`. */
export const API_URL = (process.env.EXPO_PUBLIC_API_URL?.trim() || 'http://localhost:8080/api/v1').replace(/\/+$/, '');

/** Request timeout in milliseconds. */
export const API_TIMEOUT_MS = Number(process.env.EXPO_PUBLIC_API_TIMEOUT_MS) || 15000;
