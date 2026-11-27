package com.masroofy.backend.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.masroofy.backend.repository.DashboardRepository.AccountBalanceRow;
import com.masroofy.backend.repository.DashboardRepository.MonthTotals;
import com.masroofy.backend.repository.DashboardRepository.RecentTransactionRow;
import com.masroofy.backend.support.LedgerFixtures;
import com.masroofy.backend.support.PostgresTestSupport;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneId;
import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.context.annotation.Import;
import org.springframework.jdbc.core.JdbcTemplate;

@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import({DashboardRepository.class, FxRateRepository.class})
class DashboardRepositoryTest extends PostgresTestSupport {

    private static final ZoneId CAIRO = ZoneId.of("Africa/Cairo");
    private static final Instant NOV_START = Instant.parse("2026-10-31T22:00:00Z");   // 1 Nov 00:00 Cairo
    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");
    private static final Instant CREATED = Instant.parse("2026-09-01T00:00:00Z");

    @Autowired
    private DashboardRepository repository;
    @Autowired
    private FxRateRepository fxRates;
    @Autowired
    private JdbcTemplate jdbc;

    private LedgerFixtures fx;
    private UUID user;
    private UUID cib;
    private UUID cash;

    @BeforeEach
    void setUp() {
        fx = new LedgerFixtures(jdbc);
        user = fx.user("dash-" + UUID.randomUUID() + "@example.com");
        cib = fx.account(user, "CIB Account", "bank", "EGP", "5000.00", CREATED);
        cash = fx.account(user, "Cash", "cash", "EGP", "1000.00", CREATED);
    }

    @Test
    void monthTotalsCountOnlyConfirmedNotDeletedIncomeAndExpenseInTheWindow() {
        fx.income(user, cib, "30000.00", NOV_START.plusSeconds(3600), "Salary");
        fx.expense(user, cib, "850.00", NOW.minusSeconds(60), "Carrefour");
        fx.tx(user, cib, LedgerFixtures.GROCERIES, "expense", "340.00", "EGP", "1", NOW.minusSeconds(30), "Starbucks",
                "pending_review", false);
        fx.tx(user, cib, LedgerFixtures.GROCERIES, "expense", "999.00", "EGP", "1", NOW.minusSeconds(20), "Dup",
                "confirmed", true);
        fx.transfer(user, cib, cash, "4000.00", "EGP", NOW.minusSeconds(3600));
        fx.expense(user, cib, "111.00", NOV_START.minusSeconds(1), "Last second of October");
        fx.expense(user, cib, "222.00", NOW, "Exactly at asOf (excluded)");
        UUID other = fx.user("other-" + UUID.randomUUID() + "@example.com");
        UUID otherAccount = fx.account(other, "Theirs", "cash", "EGP", "0", CREATED);
        fx.expense(other, otherAccount, "5000.00", NOW.minusSeconds(10), "Someone else");

        MonthTotals totals = repository.monthTotals(user, NOV_START, NOW);

        assertThat(totals.income()).isEqualByComparingTo("30000.00");
        assertThat(totals.expense()).isEqualByComparingTo("850.00");
    }

    @Test
    void monthTotalsConvertWithEachTransactionsOwnRateRoundedPerRow() {
        UUID usd = fx.account(user, "USD", "e_wallet", "USD", "0", CREATED);
        fx.tx(user, usd, LedgerFixtures.SALARY, "income", "350.00", "USD", "48.20", NOW.minusSeconds(100), "Upwork",
                "confirmed", false);
        // 0.01 * 0.5 = 0.005 -> 0.01 per row (half away from zero), twice = 0.02
        fx.tx(user, usd, LedgerFixtures.GROCERIES, "expense", "0.01", "USD", "0.5", NOW.minusSeconds(90), "a",
                "confirmed", false);
        fx.tx(user, usd, LedgerFixtures.GROCERIES, "expense", "0.01", "USD", "0.5", NOW.minusSeconds(80), "b",
                "confirmed", false);

        MonthTotals totals = repository.monthTotals(user, NOV_START, NOW);

        assertThat(totals.income()).isEqualByComparingTo("16870.00");
        assertThat(totals.expense()).isEqualByComparingTo("0.02");
    }

    @Test
    void emptyMonthIsZeroNotNull() {
        MonthTotals totals = repository.monthTotals(user, NOV_START, NOW);

        assertThat(totals.income()).isEqualByComparingTo("0");
        assertThat(totals.expense()).isEqualByComparingTo("0");
    }

    @Test
    void balancesAreOpeningPlusInflowsMinusOutflowsBeforeAsOf() {
        fx.income(user, cib, "30000.00", NOV_START.plusSeconds(3600), "Salary");
        fx.expense(user, cib, "850.00", NOW.minusSeconds(60), "Carrefour");
        fx.transfer(user, cib, cash, "4000.00", "EGP", NOW.minusSeconds(3600));
        fx.tx(user, cash, LedgerFixtures.TRANSPORT, "expense", "120.00", "EGP", "1", NOW.minusSeconds(50), "Uber",
                "confirmed", false);
        fx.tx(user, cib, LedgerFixtures.GROCERIES, "expense", "340.00", "EGP", "1", NOW.minusSeconds(30), "Pending",
                "pending_review", false);
        fx.expense(user, cash, "500.00", NOW.plusSeconds(60), "After asOf");
        UUID archived = fx.account(user, "Old", "cash", "EGP", "50.00", CREATED);
        jdbc.update("UPDATE accounts SET is_archived = TRUE WHERE id = ?", archived);
        fx.account(user, "Opened later", "cash", "EGP", "70.00", NOW.plusSeconds(3600));

        List<AccountBalanceRow> rows = repository.accountBalances(user, NOW);

        assertThat(rows).extracting(AccountBalanceRow::name).containsExactly("CIB Account", "Cash");
        assertThat(rows.get(0).balance()).isEqualByComparingTo("30150.00");   // 5000 + 30000 - 850 - 4000
        assertThat(rows.get(1).balance()).isEqualByComparingTo("4880.00");    // 1000 + 4000 - 120
    }

    @Test
    void overallBudgetIsTheLatestOneStartingOnOrBeforeTheMonth() {
        fx.overallMonthlyBudget(user, "15000.00", LocalDate.of(2026, 9, 1), false);
        UUID october = fx.overallMonthlyBudget(user, "18000.00", LocalDate.of(2026, 10, 1), false);
        fx.overallMonthlyBudget(user, "20000.00", LocalDate.of(2026, 12, 1), false);
        jdbc.update("""
                INSERT INTO budgets (id, user_id, category_id, amount, period, start_date, rollover,
                                     alert_threshold_pct, created_at, updated_at)
                VALUES (?, ?, ?, 3000, 'monthly', '2026-11-01', FALSE, 80, now(), now())""",
                UUID.randomUUID(), user, LedgerFixtures.GROCERIES);

        assertThat(repository.overallMonthlyBudget(user, LocalDate.of(2026, 11, 1)))
                .get().satisfies(b -> {
                    assertThat(b.id()).isEqualTo(october);
                    assertThat(b.amount()).isEqualByComparingTo("18000.00");
                    assertThat(b.alertThresholdPct()).isEqualTo(80);
                });
        assertThat(repository.overallMonthlyBudget(user, LocalDate.of(2026, 8, 1))).isEmpty();
    }

    @Test
    void monthlyExpensesGroupByCalendarMonthInTheUsersTimeZone() {
        // 31 Oct 23:30 UTC is 1 Nov 01:30 in Cairo, so it belongs to November.
        fx.expense(user, cib, "100.00", Instant.parse("2026-10-31T23:30:00Z"), "Late night");
        fx.expense(user, cib, "250.00", Instant.parse("2026-10-15T10:00:00Z"), "October");
        fx.income(user, cib, "999.00", Instant.parse("2026-10-16T10:00:00Z"), "Not an expense");

        var totals = repository.monthlyExpenses(user, CAIRO, Instant.parse("2026-09-30T21:00:00Z"), NOW);

        assertThat(totals).containsOnlyKeys(YearMonth.of(2026, 10), YearMonth.of(2026, 11));
        assertThat(totals.get(YearMonth.of(2026, 10))).isEqualByComparingTo("250.00");
        assertThat(totals.get(YearMonth.of(2026, 11))).isEqualByComparingTo("100.00");
    }

    @Test
    void recentListsNewestFirstWithCategoryAndOneRowPerTransfer() {
        fx.expense(user, cib, "250.00", NOW.minusSeconds(300), "Vodafone");
        fx.tx(user, cash, LedgerFixtures.TRANSPORT, "expense", "120.00", "EGP", "1", NOW.minusSeconds(200), "Uber",
                "confirmed", false);
        fx.transfer(user, cib, cash, "4000.00", "EGP", NOW.minusSeconds(150));
        fx.expense(user, cib, "850.00", NOW.minusSeconds(100), "Carrefour");
        fx.tx(user, cib, LedgerFixtures.GROCERIES, "expense", "340.00", "EGP", "1", NOW.minusSeconds(50), "Pending",
                "pending_review", false);

        List<RecentTransactionRow> rows = repository.recentTransactions(user, NOW, 10);

        assertThat(rows).extracting(RecentTransactionRow::merchant)
                .containsExactly("Carrefour", null, "Uber", "Vodafone");
        RecentTransactionRow carrefour = rows.get(0);
        assertThat(carrefour.categoryKey()).isEqualTo("groceries");
        assertThat(carrefour.categoryName()).isEqualTo("Groceries");
        assertThat(carrefour.accountName()).isEqualTo("CIB Account");
        RecentTransactionRow transfer = rows.get(1);
        assertThat(transfer.type()).isEqualTo("transfer_out");
        assertThat(transfer.accountName()).isEqualTo("CIB Account");
        assertThat(transfer.counterpartAccountName()).isEqualTo("Cash");
        assertThat(rows.get(2).categoryKey()).isEqualTo("transport");

        assertThat(repository.recentTransactions(user, NOW, 2)).hasSize(2);
    }

    @Test
    void pendingReviewCountIgnoresDeletedAndOtherUsers() {
        fx.tx(user, cib, LedgerFixtures.GROCERIES, "expense", "1.00", "EGP", "1", NOW, "p1", "pending_review", false);
        fx.tx(user, cib, LedgerFixtures.GROCERIES, "expense", "1.00", "EGP", "1", NOW, "p2", "pending_review", true);
        UUID other = fx.user("other-" + UUID.randomUUID() + "@example.com");
        UUID otherAccount = fx.account(other, "Theirs", "cash", "EGP", "0", CREATED);
        fx.tx(other, otherAccount, LedgerFixtures.GROCERIES, "expense", "1.00", "EGP", "1", NOW, "p3",
                "pending_review", false);

        assertThat(repository.pendingReviewCount(user)).isEqualTo(1);
    }

    @Test
    void latestPriceIsTheNewestQuoteAtOrBeforeAsOf() {
        fx.quote(LedgerFixtures.USD_EGP, "48.20", NOW.minusSeconds(86_400 * 30L));
        fx.quote(LedgerFixtures.USD_EGP, "48.50", NOW.minusSeconds(3600));
        fx.quote(LedgerFixtures.USD_EGP, "49.00", NOW.plusSeconds(3600));

        assertThat(fxRates.latestPrice("USD-EGP", NOW)).get().satisfies(p -> assertThat(p).isEqualByComparingTo("48.50"));
        assertThat(fxRates.latestPrice("USD-EGP", NOW.minusSeconds(86_400 * 10L)))
                .get().satisfies(p -> assertThat(p).isEqualByComparingTo("48.20"));
        assertThat(fxRates.latestPrice("USD-EGP", NOW.minusSeconds(86_400 * 60L))).isEmpty();
        assertThat(fxRates.latestPrice("JPY-EGP", NOW)).isEmpty();
    }
}
