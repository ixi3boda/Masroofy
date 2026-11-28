package com.masroofy.backend.model;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.UUID;

/**
 * A manually entered income or expense, ready to insert into TRANSACTION. {@code amount} is positive and in the
 * account's {@code currency}; {@code fxRateToBase} is base-currency units per 1 unit of it.
 */
public record NewTransaction(
        UUID id,
        UUID userId,
        UUID accountId,
        UUID categoryId,
        String type,
        BigDecimal amount,
        String currency,
        BigDecimal fxRateToBase,
        Instant occurredAt,
        String merchant,
        String note,
        String fingerprint,
        UUID clientRequestId,
        Instant createdAt) {

    public static final String SOURCE_MANUAL = "manual";
    public static final String STATUS_CONFIRMED = "confirmed";
}
