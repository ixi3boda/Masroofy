package com.masroofy.backend.dto.response;

/**
 * Returned whenever a code is (or would be) emailed. The app shows {@code maskedEmail} ("m***@example.com"),
 * renders {@code codeLength} boxes and disables "Resend code" for {@code resendAvailableInSeconds}.
 */
public record CodeDispatchResponse(
        String maskedEmail,
        int codeLength,
        long expiresInSeconds,
        long resendAvailableInSeconds) {
}
