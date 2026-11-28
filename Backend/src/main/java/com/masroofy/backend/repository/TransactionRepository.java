package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.fromDb;
import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import com.masroofy.backend.model.NewTransaction;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.jdbc.core.RowMapper;
import org.springframework.stereotype.Repository;

/** Writes and reads single income / expense transactions. */
@Repository
public class TransactionRepository {

    /** One transaction with the names the app shows (account, category). */
    public record TransactionRow(UUID id, String type, BigDecimal amount, String currency, BigDecimal fxRateToBase,
                                 Instant occurredAt, String merchant, String note, String source, String status,
                                 UUID categoryId, String categoryKey, String categoryName,
                                 UUID accountId, String accountName, UUID clientRequestId, Instant createdAt) {
    }

    private static final String SELECT_ROW = """
            SELECT t.id, t.type, t.amount, t.currency, t.fx_rate_to_base, t.occurred_at, t.merchant, t.note,
                   t.source, t.status, t.client_request_id, t.created_at,
                   c.id AS category_id, c.icon AS category_key, c.name AS category_name,
                   a.id AS account_id, a.name AS account_name
            FROM transactions t
            JOIN accounts a ON a.id = t.account_id
            LEFT JOIN categories c ON c.id = t.category_id
            """;

    private static final RowMapper<TransactionRow> ROW_MAPPER = (rs, rowNum) -> new TransactionRow(
            rs.getObject("id", UUID.class),
            rs.getString("type"),
            rs.getBigDecimal("amount"),
            rs.getString("currency"),
            rs.getBigDecimal("fx_rate_to_base"),
            fromDb(rs, "occurred_at"),
            rs.getString("merchant"),
            rs.getString("note"),
            rs.getString("source"),
            rs.getString("status"),
            rs.getObject("category_id", UUID.class),
            rs.getString("category_key"),
            rs.getString("category_name"),
            rs.getObject("account_id", UUID.class),
            rs.getString("account_name"),
            rs.getObject("client_request_id", UUID.class),
            fromDb(rs, "created_at"));

    private final JdbcTemplate jdbcTemplate;

    public TransactionRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /**
     * Inserts a confirmed, manual transaction.
     *
     * @throws org.springframework.dao.DuplicateKeyException when the user already used {@code clientRequestId}
     */
    public void insert(NewTransaction tx) {
        jdbcTemplate.update("""
                INSERT INTO transactions (id, user_id, account_id, category_id, type, amount, currency,
                                          fx_rate_to_base, occurred_at, merchant, note, source, status,
                                          fingerprint, client_request_id, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                tx.id(), tx.userId(), tx.accountId(), tx.categoryId(), tx.type(), tx.amount(), tx.currency(),
                tx.fxRateToBase(), toDb(tx.occurredAt()), tx.merchant(), tx.note(), NewTransaction.SOURCE_MANUAL,
                NewTransaction.STATUS_CONFIRMED, tx.fingerprint(), tx.clientRequestId(), toDb(tx.createdAt()),
                toDb(tx.createdAt()));
    }

    /** The user's transaction, unless it was deleted. Another user's id is simply not found. */
    public Optional<TransactionRow> findVisible(UUID userId, UUID id) {
        return jdbcTemplate.query(SELECT_ROW + "WHERE t.id = ? AND t.user_id = ? AND NOT t.is_deleted",
                ROW_MAPPER, id, userId).stream().findFirst();
    }

    /** The transaction an earlier request with this {@code clientRequestId} created, if any. */
    public Optional<TransactionRow> findByClientRequestId(UUID userId, UUID clientRequestId) {
        return jdbcTemplate.query(SELECT_ROW + "WHERE t.user_id = ? AND t.client_request_id = ?",
                ROW_MAPPER, userId, clientRequestId).stream().findFirst();
    }
}
