package com.masroofy.backend.model;

import java.time.Instant;
import java.util.UUID;

/** ACCOUNT entity (entity doc v2, section 2). The balance is never stored: it is computed from the transactions. */
public record Account(
        UUID id,
        UUID userId,
        String name,
        String type,
        String currency,
        String cardLast4,
        boolean archived,
        Instant createdAt) {

    /** The account every user starts with (migration V5 and {@code DefaultAccountListener}). */
    public static final String DEFAULT_CASH_NAME = "Cash";
}
