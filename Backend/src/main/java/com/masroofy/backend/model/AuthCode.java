package com.masroofy.backend.model;

import java.time.Instant;
import java.util.UUID;

/** AUTH_CODE entity: a one-time code or token. Only its HMAC is stored. */
public record AuthCode(
        UUID id,
        UUID userId,
        AuthCodePurpose purpose,
        String codeHash,
        int attempts,
        Instant expiresAt,
        Instant consumedAt,
        Instant createdAt) {

    public boolean isActive(Instant now) {
        return consumedAt == null && expiresAt.isAfter(now);
    }
}
