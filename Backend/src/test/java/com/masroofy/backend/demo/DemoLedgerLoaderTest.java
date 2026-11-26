package com.masroofy.backend.demo;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.masroofy.backend.support.LedgerFixtures;
import com.masroofy.backend.support.PostgresTestSupport;
import java.math.BigDecimal;
import java.util.UUID;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.transaction.annotation.Propagation;
import org.springframework.transaction.annotation.Transactional;

/** The demo ledger on real PostgreSQL, committed (so the deferred transfer check runs too). */
@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Transactional(propagation = Propagation.NOT_SUPPORTED)
@Import(DemoLedgerLoader.class)
class DemoLedgerLoaderTest extends PostgresTestSupport {

    @Autowired
    private DemoLedgerLoader loader;
    @Autowired
    private JdbcTemplate jdbc;

    @AfterEach
    void cleanUp() {
        jdbc.update("DELETE FROM users WHERE email LIKE 'loader-%'");
        jdbc.update("DELETE FROM price_quotes WHERE source_api = 'demo'");
    }

    private BigDecimal thisMonth(UUID user, String type) {
        return jdbc.queryForObject("""
                SELECT COALESCE(SUM(ROUND(amount * fx_rate_to_base, 2)), 0) FROM transactions
                WHERE user_id = ? AND type = ? AND status = 'confirmed' AND NOT is_deleted
                  AND occurred_at >= date_trunc('month', now() AT TIME ZONE 'Africa/Cairo') AT TIME ZONE 'Africa/Cairo'
                  AND occurred_at < now()""", BigDecimal.class, user, type);
    }

    private BigDecimal balance(UUID user, String account) {
        return jdbc.queryForObject("""
                SELECT a.opening_balance + COALESCE(SUM(CASE WHEN t.type IN ('income', 'transfer_in') THEN t.amount
                                                             ELSE -t.amount END), 0)
                FROM accounts a LEFT JOIN transactions t ON t.account_id = a.id AND t.status = 'confirmed'
                                                       AND NOT t.is_deleted
                WHERE a.user_id = ? AND a.name = ? GROUP BY a.id""", BigDecimal.class, user, account);
    }

    @Test
    void loadsTheDesignNumbersForEachUserSeparately() {
        LedgerFixtures fx = new LedgerFixtures(jdbc);
        UUID mariam = fx.user("loader-mariam-" + UUID.randomUUID() + "@example.com");
        UUID omar = fx.user("loader-omar-" + UUID.randomUUID() + "@example.com");

        assertThat(loader.load(mariam)).isEqualTo(52);
        assertThat(loader.load(omar)).isEqualTo(52);

        for (UUID user : new UUID[] {mariam, omar}) {
            assertThat(thisMonth(user, "income")).isEqualByComparingTo("30000.00");
            assertThat(thisMonth(user, "expense")).isEqualByComparingTo("12450.00");
            assertThat(balance(user, "CIB Account")).isEqualByComparingTo("20550.00");
            assertThat(balance(user, "Cash")).isEqualByComparingTo("4000.00");
            assertThat(balance(user, "Payoneer USD")).isEqualByComparingTo("300.00");
        }
        assertThat(jdbc.queryForObject("SELECT count(*) FROM transactions WHERE occurred_at > now()", Integer.class))
                .isZero();
    }

    @Test
    void reloadingReplacesOnlyThatUsersData() {
        LedgerFixtures fx = new LedgerFixtures(jdbc);
        UUID mariam = fx.user("loader-a-" + UUID.randomUUID() + "@example.com");
        UUID omar = fx.user("loader-b-" + UUID.randomUUID() + "@example.com");
        loader.load(mariam);
        loader.load(omar);
        UUID omarCash = jdbc.queryForObject("SELECT id FROM accounts WHERE user_id = ? AND name = 'Cash'", UUID.class,
                omar);
        fx.expense(omar, omarCash, "99.00", java.time.Instant.now().minusSeconds(60), "Omar's own entry");

        loader.load(mariam);

        assertThat(jdbc.queryForObject("SELECT count(*) FROM transactions WHERE user_id = ?", Integer.class, mariam))
                .isEqualTo(52);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM transactions WHERE user_id = ?", Integer.class, omar))
                .isEqualTo(53);
        assertThat(jdbc.queryForObject("SELECT count(*) FROM accounts WHERE user_id = ?", Integer.class, mariam))
                .isEqualTo(3);
    }

    @Test
    void refusesAnUnknownUserOrANonEgpUser() {
        LedgerFixtures fx = new LedgerFixtures(jdbc);
        UUID dollars = fx.user("loader-usd-" + UUID.randomUUID() + "@example.com");
        jdbc.update("UPDATE users SET base_currency = 'USD' WHERE id = ?", dollars);

        assertThatThrownBy(() -> loader.load(UUID.randomUUID())).hasMessageContaining("No Masroofy user");
        assertThatThrownBy(() -> loader.load(dollars)).hasMessageContaining("base currency is USD");
        assertThat(jdbc.queryForObject("SELECT count(*) FROM accounts WHERE user_id = ?", Integer.class, dollars))
                .isZero();
    }
}
