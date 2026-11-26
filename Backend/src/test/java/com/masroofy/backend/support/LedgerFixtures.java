package com.masroofy.backend.support;

import java.math.BigDecimal;
import java.sql.Timestamp;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;

/** Inserts users, accounts, transactions, transfers, budgets and quotes for database tests. */
public final class LedgerFixtures {

    public static final UUID GROCERIES = UUID.fromString("0c0a0000-0000-4000-8000-000000000001");
    public static final UUID TRANSPORT = UUID.fromString("0c0a0000-0000-4000-8000-000000000002");
    public static final UUID SALARY = UUID.fromString("0c0a0000-0000-4000-8000-000000000101");
    public static final UUID USD_EGP = UUID.fromString("0a55e700-0000-4000-8000-000000000001");

    private final JdbcTemplate jdbc;

    public LedgerFixtures(JdbcTemplate jdbc) {
        this.jdbc = jdbc;
    }

    private static Timestamp ts(Instant instant) {
        return Timestamp.from(instant);
    }

    public UUID user(String email) {
        UUID id = UUID.randomUUID();
        jdbc.update("""
                INSERT INTO users (id, firebase_uid, email, full_name, email_verified_at, terms_accepted_at,
                                   created_at, updated_at)
                VALUES (?, ?, ?, 'Test User', now(), now(), now(), now())""", id, "uid-" + id, email);
        return id;
    }

    public UUID account(UUID userId, String name, String type, String currency, String opening, Instant createdAt) {
        UUID id = UUID.randomUUID();
        jdbc.update("""
                INSERT INTO accounts (id, user_id, name, type, currency, opening_balance, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                id, userId, name, type, currency, new BigDecimal(opening), ts(createdAt), ts(createdAt));
        return id;
    }

    public UUID tx(UUID userId, UUID accountId, UUID categoryId, String type, String amount, String currency,
                   String fx, Instant at, String merchant, String status, boolean deleted) {
        UUID id = UUID.randomUUID();
        jdbc.update("""
                INSERT INTO transactions (id, user_id, account_id, category_id, type, amount, currency,
                                          fx_rate_to_base, occurred_at, merchant, status, is_deleted,
                                          created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, now(), now())""",
                id, userId, accountId, categoryId, type, new BigDecimal(amount), currency, new BigDecimal(fx),
                ts(at), merchant, status, deleted);
        return id;
    }

    public UUID expense(UUID userId, UUID accountId, String amount, Instant at, String merchant) {
        return tx(userId, accountId, GROCERIES, "expense", amount, "EGP", "1", at, merchant, "confirmed", false);
    }

    public UUID income(UUID userId, UUID accountId, String amount, Instant at, String merchant) {
        return tx(userId, accountId, SALARY, "income", amount, "EGP", "1", at, merchant, "confirmed", false);
    }

    /** One transfer and its two legs (same currency). */
    public UUID transfer(UUID userId, UUID from, UUID to, String amount, String currency, Instant at) {
        UUID transferId = UUID.randomUUID();
        jdbc.update("INSERT INTO transfers (id, user_id, occurred_at, created_at, updated_at) VALUES (?, ?, ?, now(), now())",
                transferId, userId, ts(at));
        for (Object[] leg : new Object[][] {{from, "transfer_out"}, {to, "transfer_in"}}) {
            jdbc.update("""
                    INSERT INTO transactions (id, user_id, account_id, transfer_id, type, amount, currency,
                                              occurred_at, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, now(), now())""",
                    UUID.randomUUID(), userId, leg[0], transferId, leg[1], new BigDecimal(amount), currency, ts(at));
        }
        return transferId;
    }

    public UUID overallMonthlyBudget(UUID userId, String amount, LocalDate start, boolean rollover) {
        UUID id = UUID.randomUUID();
        jdbc.update("""
                INSERT INTO budgets (id, user_id, category_id, amount, period, start_date, rollover,
                                     alert_threshold_pct, created_at, updated_at)
                VALUES (?, ?, NULL, ?, 'monthly', ?, ?, 80, now(), now())""",
                id, userId, new BigDecimal(amount), start, rollover);
        return id;
    }

    public void quote(UUID assetId, String price, Instant asOf) {
        jdbc.update("INSERT INTO price_quotes (id, asset_id, price, as_of, source_api) VALUES (?, ?, ?, ?, 'test')",
                UUID.randomUUID(), assetId, new BigDecimal(price), ts(asOf));
    }
}
