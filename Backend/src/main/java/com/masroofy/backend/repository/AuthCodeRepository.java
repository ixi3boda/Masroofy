package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.fromDb;
import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import com.masroofy.backend.model.AuthCode;
import com.masroofy.backend.model.AuthCodePurpose;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

@Repository
public class AuthCodeRepository {

    private static final String COLUMNS =
            "id, user_id, purpose, code_hash, attempts, expires_at, consumed_at, created_at";

    static final RowMapper<AuthCode> ROW_MAPPER = (rs, rowNum) -> new AuthCode(
            rs.getObject("id", UUID.class),
            rs.getObject("user_id", UUID.class),
            AuthCodePurpose.valueOf(rs.getString("purpose")),
            rs.getString("code_hash"),
            rs.getInt("attempts"),
            fromDb(rs, "expires_at"),
            fromDb(rs, "consumed_at"),
            fromDb(rs, "created_at"));

    private final JdbcTemplate jdbcTemplate;

    public AuthCodeRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void insert(AuthCode code) {
        jdbcTemplate.update("INSERT INTO auth_codes (" + COLUMNS + ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                code.id(),
                code.userId(),
                code.purpose().name(),
                code.codeHash(),
                code.attempts(),
                toDb(code.expiresAt()),
                toDb(code.consumedAt()),
                toDb(code.createdAt()));
    }

    /**
     * Locks the user's row until the current transaction ends, so code checks and code issuing for one user run
     * one at a time. Without it, parallel requests all read "attempts &lt; max" and get past the attempt limit.
     */
    public void lockUser(UUID userId) {
        jdbcTemplate.query("SELECT id FROM users WHERE id = ? FOR UPDATE", (rs, rowNum) -> rs.getObject(1), userId);
    }

    /** The most recently issued code for this purpose, whatever its state (used for the resend cooldown). */
    public Optional<AuthCode> findLatest(UUID userId, AuthCodePurpose purpose) {
        return jdbcTemplate.query(
                "SELECT " + COLUMNS + " FROM auth_codes WHERE user_id = ? AND purpose = ? "
                        + "ORDER BY created_at DESC LIMIT 1",
                ROW_MAPPER, userId, purpose.name()).stream().findFirst();
    }

    /** The newest unconsumed, unexpired code for this purpose. */
    public Optional<AuthCode> findLatestActive(UUID userId, AuthCodePurpose purpose, Instant now) {
        return jdbcTemplate.query(
                "SELECT " + COLUMNS + " FROM auth_codes WHERE user_id = ? AND purpose = ? "
                        + "AND consumed_at IS NULL AND expires_at > ? ORDER BY created_at DESC LIMIT 1",
                ROW_MAPPER, userId, purpose.name(), toDb(now)).stream().findFirst();
    }

    public Optional<AuthCode> findActiveByHash(AuthCodePurpose purpose, String codeHash, Instant now) {
        return jdbcTemplate.query(
                "SELECT " + COLUMNS + " FROM auth_codes WHERE purpose = ? AND code_hash = ? "
                        + "AND consumed_at IS NULL AND expires_at > ?",
                ROW_MAPPER, purpose.name(), codeHash, toDb(now)).stream().findFirst();
    }

    /** Atomically records a failed attempt; returns the new attempt count, or 0 if the code is no longer active. */
    public int incrementAttempts(UUID id) {
        int updated = jdbcTemplate.update(
                "UPDATE auth_codes SET attempts = attempts + 1 WHERE id = ? AND consumed_at IS NULL", id);
        if (updated == 0) {
            return 0;
        }
        Integer attempts = jdbcTemplate.queryForObject("SELECT attempts FROM auth_codes WHERE id = ?", Integer.class, id);
        return attempts == null ? 0 : attempts;
    }

    /** Marks the code used. Returns true only for the caller that consumed it (guards against double use). */
    public boolean consume(UUID id, Instant now) {
        return jdbcTemplate.update(
                "UPDATE auth_codes SET consumed_at = ? WHERE id = ? AND consumed_at IS NULL", toDb(now), id) == 1;
    }

    /** Closes every still-open code of this purpose, so only the newest code works. */
    public int invalidateActive(UUID userId, AuthCodePurpose purpose, Instant now) {
        return jdbcTemplate.update(
                "UPDATE auth_codes SET consumed_at = ? WHERE user_id = ? AND purpose = ? AND consumed_at IS NULL",
                toDb(now), userId, purpose.name());
    }
}
