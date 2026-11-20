import { mockAuthService } from '@/mocks/services/mockAuthService';

/**
 * The auth service every screen uses. It points at the in-memory mock for now;
 * when the backend is ready, replace this export with a real implementation
 * that has the same method signatures — no screen needs to change.
 */
export const authService = mockAuthService;
