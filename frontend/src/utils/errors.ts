import { strings } from '@/strings';

/** An error whose message is safe to show the user as-is. */
export class AppError extends Error {}

/** User-facing message for anything thrown by a service call. */
export const getErrorMessage = (error: unknown): string =>
  error instanceof AppError ? error.message : strings.common.genericError;
