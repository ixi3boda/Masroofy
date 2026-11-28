package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import java.time.Instant;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/** AUDIT_LOG (entity doc v2, section 1): the history of every change to financial data. */
@Repository
public class AuditLogRepository {

    public static final String ENTITY_TRANSACTION = "transaction";
    public static final String ACTION_CREATE = "create";

    private final JdbcTemplate jdbcTemplate;

    public AuditLogRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** {@code beforeJson} / {@code afterJson} are JSON documents (or null), stored as JSONB. */
    public void insert(UUID id, UUID userId, String entity, UUID entityId, String action, String beforeJson,
                       String afterJson, Instant createdAt) {
        jdbcTemplate.update("""
                INSERT INTO audit_log (id, user_id, entity, entity_id, action, before, after, created_at)
                VALUES (?, ?, ?, ?, ?, ?::jsonb, ?::jsonb, ?)""",
                id, userId, entity, entityId, action, beforeJson, afterJson, toDb(createdAt));
    }
}
