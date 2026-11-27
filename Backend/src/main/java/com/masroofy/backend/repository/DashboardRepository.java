package com.masroofy.backend.repository;

import static com.masroofy.backend.repository.JdbcTimestamps.fromDb;
import static com.masroofy.backend.repository.JdbcTimestamps.toDb;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneId;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Repository;

/**
 * Read-only queries behind the home dashboard. Every query is scoped to one user and only counts
 * confirmed, non-deleted transactions; pending-review items appear only in {@link #pendingReviewCount}.
 */
@Repository
public class DashboardRepository {

    /** Confirmed and not deleted: the rows that count toward balances and totals. */
    private static final String COUNTED = "t.status = 'confirmed' AND NOT t.is_deleted";

    /** Each row's amount in the base currency, rounded per row so totals equal the sum of what is displayed. */
    private static final String AMOUNT_IN_BASE = "ROUND(t.amount * t.fx_rate_to_base, 2)";

    public record MonthTotals(BigDecimal income, BigDecimal expense) {
    }

    public record AccountBalanceRow(UUID id, String name, String type, String currency, String cardLast4,
                                    BigDecimal balance) {
    }

    public record BudgetRow(UUID id, BigDecimal amount, LocalDate startDate, boolean rollover,
                            int alertThresholdPct) {
    }

    public record RecentTransactionRow(UUID id, String type, BigDecimal amount, String currency,
                                       BigDecimal fxRateToBase, Instant occurredAt, String merchant, String note,
                                       UUID categoryId, String categoryName, String categoryKey,
                                       UUID accountId, String accountName,
                                       UUID counterpartAccountId, String counterpartAccountName) {
    }

    private final JdbcTemplate jdbcTemplate;

    public DashboardRepository(JdbcTemplate jdbcTemplate) {
        this.jdbcTemplate = jdbcTemplate;
    }

    /** Income and expense in the base currency for {@code [from, to)}. Transfers are neither. */
    public MonthTotals monthTotals(UUID userId, Instant from, Instant to) {
        return jdbcTemplate.queryForObject("""
                SELECT COALESCE(SUM(%1$s) FILTER (WHERE t.type = 'income'), 0)  AS income,
                       COALESCE(SUM(%1$s) FILTER (WHERE t.type = 'expense'), 0) AS expense
                FROM transactions t
                WHERE t.user_id = ? AND %2$s AND t.occurred_at >= ? AND t.occurred_at < ?
                """.formatted(AMOUNT_IN_BASE, COUNTED),
                (rs, rowNum) -> new MonthTotals(rs.getBigDecimal("income"), rs.getBigDecimal("expense")),
                userId, toDb(from), toDb(to));
    }

    /**
     * Balance of every open account at {@code asOf}, in the account's own currency:
     * opening balance + income + transfers in - expenses - transfers out.
     */
    public List<AccountBalanceRow> accountBalances(UUID userId, Instant asOf) {
        return jdbcTemplate.query("""
                SELECT a.id, a.name, a.type, a.currency, a.card_last4,
                       a.opening_balance + COALESCE(SUM(CASE WHEN t.type IN ('income', 'transfer_in') THEN t.amount
                                                             ELSE -t.amount END), 0) AS balance
                FROM accounts a
                LEFT JOIN transactions t ON t.account_id = a.id AND %s AND t.occurred_at < ?
                WHERE a.user_id = ? AND NOT a.is_archived AND a.created_at < ?
                GROUP BY a.id
                ORDER BY a.created_at, a.name
                """.formatted(COUNTED),
                (rs, rowNum) -> new AccountBalanceRow(
                        rs.getObject("id", UUID.class),
                        rs.getString("name"),
                        rs.getString("type"),
                        rs.getString("currency"),
                        rs.getString("card_last4"),
                        rs.getBigDecimal("balance")),
                toDb(asOf), userId, toDb(asOf));
    }

    /** The overall (no category) monthly budget in force for the month starting on {@code monthStart}. */
    public Optional<BudgetRow> overallMonthlyBudget(UUID userId, LocalDate monthStart) {
        return jdbcTemplate.query("""
                SELECT id, amount, start_date, rollover, alert_threshold_pct
                FROM budgets
                WHERE user_id = ? AND category_id IS NULL AND period = 'monthly' AND start_date <= ?
                ORDER BY start_date DESC
                LIMIT 1
                """,
                (rs, rowNum) -> new BudgetRow(
                        rs.getObject("id", UUID.class),
                        rs.getBigDecimal("amount"),
                        rs.getObject("start_date", LocalDate.class),
                        rs.getBoolean("rollover"),
                        rs.getInt("alert_threshold_pct")),
                userId, monthStart).stream().findFirst();
    }

    /** Expenses in the base currency per calendar month of {@code zone}, for {@code [from, to)}. */
    public Map<YearMonth, BigDecimal> monthlyExpenses(UUID userId, ZoneId zone, Instant from, Instant to) {
        Map<YearMonth, BigDecimal> totals = new LinkedHashMap<>();
        jdbcTemplate.query("""
                SELECT to_char(t.occurred_at AT TIME ZONE ?, 'YYYY-MM') AS month, SUM(%s) AS total
                FROM transactions t
                WHERE t.user_id = ? AND t.type = 'expense' AND %s AND t.occurred_at >= ? AND t.occurred_at < ?
                GROUP BY 1
                ORDER BY 1
                """.formatted(AMOUNT_IN_BASE, COUNTED),
                rs -> {
                    totals.put(YearMonth.parse(rs.getString("month")), rs.getBigDecimal("total"));
                },
                zone.getId(), userId, toDb(from), toDb(to));
        return totals;
    }

    /**
     * The newest counted transactions before {@code asOf}. A transfer is listed once, as its outgoing leg,
     * with the receiving account as counterpart.
     */
    public List<RecentTransactionRow> recentTransactions(UUID userId, Instant asOf, int limit) {
        return jdbcTemplate.query("""
                SELECT t.id, t.type, t.amount, t.currency, t.fx_rate_to_base, t.occurred_at, t.merchant, t.note,
                       c.id AS category_id, c.name AS category_name, c.icon AS category_key,
                       a.id AS account_id, a.name AS account_name,
                       oa.id AS counterpart_account_id, oa.name AS counterpart_account_name
                FROM transactions t
                JOIN accounts a ON a.id = t.account_id
                LEFT JOIN categories c ON c.id = t.category_id
                LEFT JOIN transactions o ON o.transfer_id = t.transfer_id AND o.id <> t.id
                LEFT JOIN accounts oa ON oa.id = o.account_id
                WHERE t.user_id = ? AND %s AND t.type <> 'transfer_in' AND t.occurred_at < ?
                ORDER BY t.occurred_at DESC, t.id DESC
                LIMIT ?
                """.formatted(COUNTED),
                (rs, rowNum) -> new RecentTransactionRow(
                        rs.getObject("id", UUID.class),
                        rs.getString("type"),
                        rs.getBigDecimal("amount"),
                        rs.getString("currency"),
                        rs.getBigDecimal("fx_rate_to_base"),
                        fromDb(rs, "occurred_at"),
                        rs.getString("merchant"),
                        rs.getString("note"),
                        rs.getObject("category_id", UUID.class),
                        rs.getString("category_name"),
                        rs.getString("category_key"),
                        rs.getObject("account_id", UUID.class),
                        rs.getString("account_name"),
                        rs.getObject("counterpart_account_id", UUID.class),
                        rs.getString("counterpart_account_name")),
                userId, toDb(asOf), limit);
    }

    /** Captured transactions (SMS, receipt, voice) still waiting for the user to confirm them. */
    public long pendingReviewCount(UUID userId) {
        Long count = jdbcTemplate.queryForObject(
                "SELECT count(*) FROM transactions WHERE user_id = ? AND status = 'pending_review' AND NOT is_deleted",
                Long.class, userId);
        return count == null ? 0 : count;
    }
}
