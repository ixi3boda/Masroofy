package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.fromDb;
import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import com.masroofy.backend.model.User;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

@Repository
public class UserRepository {

    private static final String COLUMNS = """
            id, firebase_uid, email, phone, full_name, base_currency, locale, timezone, fcm_token,
            email_verified_at, terms_accepted_at, created_at, updated_at, session_version""";

    static final RowMapper<User> ROW_MAPPER = (rs, rowNum) -> new User(
            rs.getObject("id", UUID.class),
            rs.getString("firebase_uid"),
            rs.getString("email"),
            rs.getString("phone"),
            rs.getString("full_name"),
            rs.getString("base_currency"),
            rs.getString("locale"),
            rs.getString("timezone"),
            rs.getString("fcm_token"),
            fromDb(rs, "email_verified_at"),
            fromDb(rs, "terms_accepted_at"),
            fromDb(rs, "created_at"),
            fromDb(rs, "updated_at"),
            rs.getInt("session_version"));

    private final JdbcTemplate jdbcTemplate;

    public UserRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    public void insert(User user) {
        jdbcTemplate.update("INSERT INTO users (" + COLUMNS + ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                user.id(),
                user.firebaseUid(),
                user.email(),
                user.phone(),
                user.fullName(),
                user.baseCurrency(),
                user.locale(),
                user.timezone(),
                user.fcmToken(),
                toDb(user.emailVerifiedAt()),
                toDb(user.termsAcceptedAt()),
                toDb(user.createdAt()),
                toDb(user.updatedAt()),
                user.sessionVersion());
    }

    public Optional<User> findById(UUID id) {
        return jdbcTemplate.query("SELECT " + COLUMNS + " FROM users WHERE id = ?", ROW_MAPPER, id)
                .stream().findFirst();
    }

    /** {@code email} must already be normalised (trimmed, lower case). */
    public Optional<User> findByEmail(String email) {
        return jdbcTemplate.query("SELECT " + COLUMNS + " FROM users WHERE email = ?", ROW_MAPPER, email)
                .stream().findFirst();
    }

    public Optional<User> findByFirebaseUid(String firebaseUid) {
        return jdbcTemplate.query("SELECT " + COLUMNS + " FROM users WHERE firebase_uid = ?", ROW_MAPPER, firebaseUid)
                .stream().findFirst();
    }

    /**
     * Serializes work on one email address until the current transaction ends (PostgreSQL advisory lock on a hash
     * of the email; an unrelated email that hashes the same only waits a little).
     */
    public void lockEmail(String email) {
        jdbcTemplate.query("SELECT pg_advisory_xact_lock(hashtext(?))", (rs, rowNum) -> 1, email);
    }

    public boolean existsByEmail(String email) {
        Boolean exists = jdbcTemplate.queryForObject(
                "SELECT EXISTS (SELECT 1 FROM users WHERE email = ?)", Boolean.class, email);
        return Boolean.TRUE.equals(exists);
    }

    /** Sets email_verified_at once; returns the number of rows changed (0 if already verified). */
    public int markEmailVerified(UUID id, Instant verifiedAt) {
        return jdbcTemplate.update(
                "UPDATE users SET email_verified_at = ?, updated_at = ? WHERE id = ? AND email_verified_at IS NULL",
                toDb(verifiedAt), toDb(verifiedAt), id);
    }

    /** Points the profile at a (re)created Firebase account. Returns the number of rows changed. */
    public int relinkFirebaseUid(UUID id, String firebaseUid, Instant at) {
        return jdbcTemplate.update("UPDATE users SET firebase_uid = ?, updated_at = ? WHERE id = ?",
                firebaseUid, toDb(at), id);
    }

    /** Raises session_version to {@code version}; it never goes down. Returns the number of rows changed. */
    public int raiseSessionVersion(UUID id, int version) {
        return jdbcTemplate.update(
                "UPDATE users SET session_version = GREATEST(session_version, ?) WHERE id = ?", version, id);
    }
}
