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

    private BigDecimal overallBudget(UUID user) {
        return jdbc.queryForObject("SELECT amount FROM budgets WHERE user_id = ? AND category_id IS NULL",
                BigDecimal.class, user);
    }

    @Test
    void eachProfileHasItsOwnNumbers() {
        LedgerFixtures fx = new LedgerFixtures(jdbc);
        UUID saver = fx.user("loader-saver-" + UUID.randomUUID() + "@example.com");
        UUID freelancer = fx.user("loader-freelancer-" + UUID.randomUUID() + "@example.com");

        assertThat(loader.load(saver, "saver")).isEqualTo(47);
        assertThat(loader.load(freelancer, "freelancer")).isEqualTo(50);

        assertThat(thisMonth(saver, "income")).isEqualByComparingTo("43200.00");
        assertThat(thisMonth(saver, "expense")).isEqualByComparingTo("10065.00");
        assertThat(balance(saver, "CIB Account")).isEqualByComparingTo("43830.00");
        assertThat(balance(saver, "Cash")).isEqualByComparingTo("3305.00");
        assertThat(balance(saver, "Payoneer USD")).isEqualByComparingTo("300.00");
        assertThat(overallBudget(saver)).isEqualByComparingTo("15000.00");

        assertThat(thisMonth(freelancer, "income")).isEqualByComparingTo("34125.00");
        assertThat(thisMonth(freelancer, "expense")).isEqualByComparingTo("30937.50");
        assertThat(balance(freelancer, "NBE Account")).isEqualByComparingTo("31880.00");
        assertThat(balance(freelancer, "Cash")).isEqualByComparingTo("3350.00");
        assertThat(balance(freelancer, "Payoneer USD")).isEqualByComparingTo("495.00");
        assertThat(overallBudget(freelancer)).isEqualByComparingTo("25000.00");

        UUID student = fx.user("loader-student-" + UUID.randomUUID() + "@example.com");
        UUID family = fx.user("loader-family-" + UUID.randomUUID() + "@example.com");
        assertThat(loader.load(student, "student")).isEqualTo(48);
        assertThat(loader.load(family, "family")).isEqualTo(51);

        assertThat(thisMonth(student, "income")).isEqualByComparingTo("11000.00");
        assertThat(thisMonth(student, "expense")).isEqualByComparingTo("4580.00");
        assertThat(balance(student, "Banque Misr")).isEqualByComparingTo("15685.00");
        assertThat(balance(student, "Cash")).isEqualByComparingTo("2035.00");
        assertThat(overallBudget(student)).isEqualByComparingTo("6000.00");

        assertThat(thisMonth(family, "income")).isEqualByComparingTo("62000.00");
        assertThat(thisMonth(family, "expense")).isEqualByComparingTo("45980.00");
        assertThat(balance(family, "QNB Account")).isEqualByComparingTo("34130.00");
        assertThat(balance(family, "Cash")).isEqualByComparingTo("4890.00");
        assertThat(overallBudget(family)).isEqualByComparingTo("50000.00");

        assertThat(jdbc.queryForObject("SELECT count(*) FROM transactions WHERE occurred_at > now()", Integer.class))
                .isZero();
    }

    @Test
    void blankProfileMeansStandardAndAnUnknownOneIsRefused() {
        LedgerFixtures fx = new LedgerFixtures(jdbc);
        UUID user = fx.user("loader-profile-" + UUID.randomUUID() + "@example.com");

        assertThat(loader.load(user, " ")).isEqualTo(52);
        assertThat(thisMonth(user, "income")).isEqualByComparingTo("30000.00");
        assertThatThrownBy(() -> loader.load(user, "spender")).hasMessageContaining("Unknown demo profile");
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
