package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.fromDb;
import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import com.masroofy.backend.model.AuthCodePurpose;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/** Per-email resend cooldown ({@code code_dispatches}), keyed by an HMAC of the email. */
@Repository
public class CodeDispatchRepository {

    private final JdbcTemplate jdbcTemplate;

    public CodeDispatchRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * Atomically takes the send slot for this email and purpose unless one was taken after {@code notAfter}.
     *
     * @return empty when the slot was taken by this call; otherwise the time the current slot was taken
     */
    public Optional<Instant> reserve(String emailHash, AuthCodePurpose purpose, Instant now, Instant notAfter) {
        List<Instant> taken = jdbcTemplate.query("""
                        INSERT INTO code_dispatches (email_hash, purpose, last_sent_at) VALUES (?, ?, ?)
                        ON CONFLICT (email_hash, purpose) DO UPDATE SET last_sent_at = EXCLUDED.last_sent_at
                        WHERE code_dispatches.last_sent_at <= ?
                        RETURNING last_sent_at""",
                (rs, rowNum) -> fromDb(rs, "last_sent_at"), emailHash, purpose.name(), toDb(now), toDb(notAfter));
        if (!taken.isEmpty()) {
            return Optional.empty();
        }
        return jdbcTemplate.query(
                "SELECT last_sent_at FROM code_dispatches WHERE email_hash = ? AND purpose = ?",
                (rs, rowNum) -> fromDb(rs, "last_sent_at"), emailHash, purpose.name()).stream().findFirst();
    }

    /** Records a send unconditionally (used at sign-up, which has its own duplicate check). */
    public void record(String emailHash, AuthCodePurpose purpose, Instant now) {
        jdbcTemplate.update("""
                        INSERT INTO code_dispatches (email_hash, purpose, last_sent_at) VALUES (?, ?, ?)
                        ON CONFLICT (email_hash, purpose) DO UPDATE SET last_sent_at = EXCLUDED.last_sent_at""",
                emailHash, purpose.name(), toDb(now));
    }

    /** Drops rows that can no longer block anything. */
    public int deleteOlderThan(Instant cutoff) {
        return jdbcTemplate.update("DELETE FROM code_dispatches WHERE last_sent_at < ?", toDb(cutoff));
    }
}
