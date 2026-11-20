import { strings } from '@/strings';

/** An error whose message is safe to show the user as-is. */
export class AppError extends Error {}

/** One entry of the backend's `fieldErrors[]`. */
export interface FieldError {
  field: string;
  code: string;
  message?: string;
}

/** Optional extra data the backend sends with some error codes. */
export interface ApiErrorDetails {
  remainingAttempts?: number;
  retryAfterSeconds?: number;
  maskedEmail?: string;
  failedRules?: string[];
}

/**
 * A failure in the backend's error format (or the same shape from the mock).
 * `code` is what the app switches on; `message` is English, for logs only.
 * Local failures use status 0 with `NETWORK_ERROR`, `TIMEOUT` or `INVALID_RESPONSE`.
 */
export class ApiError extends AppError {
  constructor(
    readonly code: string,
    readonly status: number,
    message: string = code,
    readonly fieldErrors: FieldError[] = [],
    readonly details: ApiErrorDetails = {}
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

export const isApiError = (error: unknown, code?: string): error is ApiError =>
  error instanceof ApiError && (code === undefined || error.code === code);

const describeApiError = ({ code, details }: ApiError): string => {
  const { codes } = strings.errors;
  if (code === 'INVALID_CODE') return codes.INVALID_CODE(details.remainingAttempts);
  if (code === 'RESEND_COOLDOWN') return codes.RESEND_COOLDOWN(details.retryAfterSeconds);
  const text = codes[code as keyof typeof codes];
  return typeof text === 'string' ? text : codes.INTERNAL_ERROR;
};

/** User-facing message for anything thrown by a service call. */
export const getErrorMessage = (error: unknown): string => {
  if (error instanceof ApiError) return describeApiError(error);
  return error instanceof AppError ? error.message : strings.common.genericError;
};

const describeFieldError = ({ code, message }: FieldError): string => {
  const { fields } = strings.errors;
  return fields[code as keyof typeof fields] ?? message ?? strings.common.genericError;
};

/**
 * The backend's `fieldErrors` as one message per field, keyed by the form's own
 * field names. `fieldMap` maps a backend field to a form field when they differ.
 */
export const getFieldErrors = <Field extends string>(
  error: unknown,
  fieldMap: Record<string, Field>
): Partial<Record<Field, string>> => {
  if (!(error instanceof ApiError)) return {};
  const result: Partial<Record<Field, string>> = {};
  for (const fieldError of error.fieldErrors) {
    const field = fieldMap[fieldError.field];
    if (!field) continue;
    const text = describeFieldError(fieldError);
    result[field] = result[field] ? `${result[field]} ${text}` : text;
  }
  return result;
};
