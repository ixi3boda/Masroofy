package com.masroofy.backend.model;

import java.time.Instant;
import java.util.UUID;

/** USER entity (entity doc v2). Passwords are never stored; Firebase owns credentials. */
public record User(
        UUID id,
        String firebaseUid,
        String email,
        String phone,
        String fullName,
        String baseCurrency,
        String locale,
        String timezone,
        String fcmToken,
        Instant emailVerifiedAt,
        Instant termsAcceptedAt,
        Instant createdAt,
        Instant updatedAt) {

    public static final String DEFAULT_CURRENCY = "EGP";
    public static final String DEFAULT_LOCALE = "en";
    public static final String DEFAULT_TIMEZONE = "Africa/Cairo";

    public boolean isEmailVerified() {
        return emailVerifiedAt != null;
    }
}
