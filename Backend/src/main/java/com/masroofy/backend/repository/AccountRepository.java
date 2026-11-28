package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.fromDb;
import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import com.masroofy.backend.model.Account;
import java.time.Instant;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

@Repository
public class AccountRepository {

    private static final String COLUMNS = "id, user_id, name, type, currency, card_last4, is_archived, created_at";

    private static final RowMapper<Account> ROW_MAPPER = (rs, rowNum) -> new Account(
            rs.getObject("id", UUID.class),
            rs.getObject("user_id", UUID.class),
            rs.getString("name"),
            rs.getString("type"),
            rs.getString("currency"),
            rs.getString("card_last4"),
            rs.getBoolean("is_archived"),
            fromDb(rs, "created_at"));

    private final JdbcTemplate jdbcTemplate;

    public AccountRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** The user's accounts that are not archived, oldest first (the same order as the dashboard). */
    public List<Account> findOpenByUser(UUID userId) {
        return jdbcTemplate.query("SELECT " + COLUMNS + " FROM accounts WHERE user_id = ? AND NOT is_archived "
                + "ORDER BY created_at, name", ROW_MAPPER, userId);
    }

    /** The account, only if it belongs to {@code userId} and is not archived. */
    public Optional<Account> findOpen(UUID userId, UUID accountId) {
        return jdbcTemplate.query("SELECT " + COLUMNS + " FROM accounts WHERE id = ? AND user_id = ? "
                + "AND NOT is_archived", ROW_MAPPER, accountId, userId).stream().findFirst();
    }

    /**
     * Gives the user a "Cash" account in their base currency. Does nothing if they already have an account with that
     * name (for example from demo data), so it is safe to run more than once.
     *
     * @return true when the account was created
     */
    public boolean insertDefaultCash(UUID id, UUID userId, Instant now) {
        return jdbcTemplate.update("""
                INSERT INTO accounts (id, user_id, name, type, currency, opening_balance, is_archived,
                                      created_at, updated_at)
                SELECT ?, u.id, ?, 'cash', u.base_currency, 0, FALSE, ?, ?
                FROM users u
                WHERE u.id = ?
                ON CONFLICT (user_id, name) DO NOTHING""",
                id, Account.DEFAULT_CASH_NAME, toDb(now), toDb(now), userId) == 1;
    }
}
