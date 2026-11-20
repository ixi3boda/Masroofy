package com.financeapp.sms.service;

import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;

/**
 * Outcome for one uploaded SMS.
 * status: APPLIED (balance updated), DRAFT (waiting for review), IGNORED (not a transaction),
 *         ALREADY_RECEIVED (same SMS uploaded before; nothing changed).
 */
public record IngestResult(String status, Long transactionId, String institution, String type, BigDecimal amount,
                           String currency, Instant occurredAt, Long accountId, List<String> reviewReasons) {
    public static IngestResult ignored(String institution) {
        return new IngestResult("IGNORED", null, institution, null, null, null, null, null, List.of());
    }
    public static IngestResult alreadyReceived() {
        return new IngestResult("ALREADY_RECEIVED", null, null, null, null, null, null, null, List.of());
    }
}
