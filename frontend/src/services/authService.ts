import { getDataSource } from '@/config/env';
import { mockAuthService } from '@/mocks/services/mockAuthService';
import { apiAuthService } from './api/apiAuthService';
import { AuthService } from './types';

/**
 * The auth service every screen uses. It is the in-memory mock or the real
 * backend, picked by `EXPO_PUBLIC_AUTH_SOURCE` (else `EXPO_PUBLIC_API_MODE`,
 * else `mock`). Both follow the same `AuthService` contract, so screens never
 * know which one is running.
 */
export const authService: AuthService = getDataSource('auth') === 'api' ? apiAuthService : mockAuthService;
