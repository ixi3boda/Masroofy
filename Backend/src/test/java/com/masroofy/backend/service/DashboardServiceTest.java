package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyInt;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.masroofy.backend.dto.response.DashboardResponse;
import com.masroofy.backend.dto.response.DashboardResponse.AccountSummary;
import com.masroofy.backend.dto.response.DashboardResponse.BudgetSummary;
import com.masroofy.backend.dto.response.DashboardResponse.RecentTransaction;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.DashboardRepository;
import com.masroofy.backend.repository.DashboardRepository.AccountBalanceRow;
import com.masroofy.backend.repository.DashboardRepository.BudgetRow;
import com.masroofy.backend.repository.DashboardRepository.MonthTotals;
import com.masroofy.backend.repository.DashboardRepository.RecentTransactionRow;
import com.masroofy.backend.repository.UserRepository;
import java.math.BigDecimal;
import java.time.Clock;
import java.time.Instant;
import java.time.LocalDate;
import java.time.YearMonth;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.transaction.PlatformTransactionManager;

@ExtendWith(MockitoExtension.class)
class DashboardServiceTest {

    private static final UUID USER_ID = UUID.fromString("22222222-2222-2222-2222-222222222222");
    private static final ZoneId CAIRO = ZoneId.of("Africa/Cairo");
    /** 20 Nov 2026, 12:00 in Cairo (UTC+2). */
    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");

    @Mock
    private UserRepository userRepository;
    @Mock
    private DashboardRepository dashboardRepository;
    @Mock
    private FxRateService fxRateService;

    private DashboardService service;

    private static User user(String timezone) {
        return new User(USER_ID, "uid-1", "mariam@example.com", null, "Mariam Ali", "EGP", "en", timezone, null,
                NOW, NOW, NOW, NOW);
    }

    private DashboardService serviceAt(Instant now) {
        return new DashboardService(userRepository, dashboardRepository, fxRateService,
                mock(PlatformTransactionManager.class), Clock.fixed(now, ZoneOffset.UTC));
    }

    private static BigDecimal d(String value) {
        return new BigDecimal(value);
    }

    @BeforeEach
    void setUp() {
        service = serviceAt(NOW);
        lenient().when(userRepository.findById(USER_ID)).thenReturn(Optional.of(user("Africa/Cairo")));
        lenient().when(dashboardRepository.monthTotals(any(), any(), any()))
                .thenReturn(new MonthTotals(d("30000.00"), d("12450.00")));
        lenient().when(dashboardRepository.accountBalances(any(), any())).thenReturn(List.of());
        lenient().when(dashboardRepository.overallMonthlyBudget(any(), any())).thenReturn(Optional.empty());
        lenient().when(dashboardRepository.recentTransactions(any(), any(), anyInt())).thenReturn(List.of());
        lenient().when(fxRateService.rate(eq("EGP"), eq("EGP"), any())).thenReturn(Optional.of(BigDecimal.ONE));
    }

    @Nested
    class Period {

        @Test
        void defaultsToTheCurrentMonthUpToNow() {
            DashboardResponse response = service.getDashboard(USER_ID, null, 3);

            assertThat(response.period().month()).isEqualTo("2026-11");
            assertThat(response.period().label()).isEqualTo("Nov 2026");
            assertThat(response.period().startDate()).isEqualTo(LocalDate.of(2026, 11, 1));
            assertThat(response.period().endDate()).isEqualTo(LocalDate.of(2026, 11, 30));
            assertThat(response.period().timezone()).isEqualTo("Africa/Cairo");
            assertThat(response.period().asOf()).isEqualTo(NOW);
            assertThat(response.period().currentMonth()).isTrue();
            // Midnight 1 Nov in Cairo is 22:00 on 31 Oct UTC.
            verify(dashboardRepository).monthTotals(USER_ID, Instant.parse("2026-10-31T22:00:00Z"), NOW);
        }

        @Test
        void aPastMonthEndsAtItsLastMomentInTheUsersTimeZone() {
            DashboardResponse response = service.getDashboard(USER_ID, "2026-10", 3);

            Instant octStart = Instant.parse("2026-09-30T21:00:00Z");   // Cairo is UTC+3 on 1 Oct 2026 (summer time)
            Instant novStart = Instant.parse("2026-10-31T22:00:00Z");   // and UTC+2 from 30 Oct 2026
            assertThat(response.period().asOf()).isEqualTo(novStart);
            assertThat(response.period().currentMonth()).isFalse();
            verify(dashboardRepository).monthTotals(USER_ID, octStart, novStart);
            verify(dashboardRepository).accountBalances(USER_ID, novStart);
            verify(dashboardRepository).recentTransactions(USER_ID, novStart, 3);
        }

        @Test
        void currentMonthFollowsTheUsersTimeZoneNotUtc() {
            // 31 Oct 23:30 UTC is already 1 Nov 01:30 in Cairo.
            DashboardResponse response = serviceAt(Instant.parse("2026-10-31T23:30:00Z"))
                    .getDashboard(USER_ID, null, 3);

            assertThat(response.period().month()).isEqualTo("2026-11");
        }

        @Test
        void unknownTimeZoneFallsBackToUtc() {
            when(userRepository.findById(USER_ID)).thenReturn(Optional.of(user("Mars/Olympus")));

            assertThat(service.getDashboard(USER_ID, null, 3).period().timezone()).isEqualTo("Z");
            assertThat(DashboardService.zoneOf(null)).isEqualTo(ZoneOffset.UTC);
        }

        @Test
        void rejectsFutureMalformedAndAncientMonths() {
            assertInvalid(() -> service.getDashboard(USER_ID, "2026-12", 3), "month");
            assertInvalid(() -> service.getDashboard(USER_ID, "11-2026", 3), "month");
            assertInvalid(() -> service.getDashboard(USER_ID, "2026-13", 3), "month");
            assertInvalid(() -> service.getDashboard(USER_ID, "1999-12", 3), "month");
            verify(dashboardRepository, never()).monthTotals(any(), any(), any());
        }

        @Test
        void rejectsRecentLimitOutsideOneToTwenty() {
            assertInvalid(() -> service.getDashboard(USER_ID, null, 0), "recentLimit");
            assertInvalid(() -> service.getDashboard(USER_ID, null, 21), "recentLimit");
        }

        @Test
        void unknownUserIsNotFound() {
            when(userRepository.findById(USER_ID)).thenReturn(Optional.empty());

            assertThatThrownBy(() -> service.getDashboard(USER_ID, null, 3))
                    .isInstanceOfSatisfying(ApiException.class,
                            e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.USER_NOT_FOUND));
        }
    }

    @Nested
    class Totals {

        @Test
        void summaryIsIncomeExpenseAndNetWithTwoDecimals() {
            when(dashboardRepository.monthTotals(any(), any(), any()))
                    .thenReturn(new MonthTotals(new BigDecimal("30000"), new BigDecimal("12450.5")));

            DashboardResponse response = service.getDashboard(USER_ID, null, 3);

            assertThat(response.summary().totalIncome()).hasToString("30000.00");
            assertThat(response.summary().totalExpense()).hasToString("12450.50");
            assertThat(response.summary().net()).hasToString("17549.50");
            assertThat(response.baseCurrency()).isEqualTo("EGP");
        }

        @Test
        void badgeCountsPendingReviewItems() {
            when(dashboardRepository.pendingReviewCount(USER_ID)).thenReturn(2L);

            assertThat(service.getDashboard(USER_ID, null, 3).badges().pendingReview()).isEqualTo(2);
        }
    }

    @Nested
    class Balances {

        private final UUID cib = UUID.randomUUID();
        private final UUID cash = UUID.randomUUID();
        private final UUID usd = UUID.randomUUID();

        @Test
        void convertsEachAccountAndSortsLargestFirst() {
            when(dashboardRepository.accountBalances(USER_ID, NOW)).thenReturn(List.of(
                    new AccountBalanceRow(cash, "Cash", "cash", "EGP", null, d("4000.00")),
                    new AccountBalanceRow(usd, "Payoneer USD", "e_wallet", "USD", null, d("300.00")),
                    new AccountBalanceRow(cib, "CIB Account", "bank", "EGP", "4821", d("20550.00"))));
            when(fxRateService.rate("USD", "EGP", NOW)).thenReturn(Optional.of(d("48.50000000")));

            var balance = service.getDashboard(USER_ID, null, 3).balance();

            assertThat(balance.total()).hasToString("39100.00");
            assertThat(balance.accounts()).extracting(AccountSummary::name)
                    .containsExactly("CIB Account", "Payoneer USD", "Cash");
            AccountSummary usdAccount = balance.accounts().get(1);
            assertThat(usdAccount.balance()).hasToString("300.00");
            assertThat(usdAccount.balanceInBase()).hasToString("14550.00");
            assertThat(usdAccount.fxRate()).hasToString("48.500000");
            assertThat(balance.accounts().get(0).fxRate()).isNull();
            assertThat(balance.accounts().get(0).cardLast4()).isEqualTo("4821");
            assertThat(balance.unconvertedCurrencies()).isEmpty();
        }

        @Test
        void accountsWithoutARateAreListedButLeftOutOfTheTotal() {
            when(dashboardRepository.accountBalances(USER_ID, NOW)).thenReturn(List.of(
                    new AccountBalanceRow(cib, "CIB Account", "bank", "EGP", null, d("1000.00")),
                    new AccountBalanceRow(usd, "Yen wallet", "e_wallet", "JPY", null, d("5000.00"))));
            when(fxRateService.rate("JPY", "EGP", NOW)).thenReturn(Optional.empty());

            var balance = service.getDashboard(USER_ID, null, 3).balance();

            assertThat(balance.total()).hasToString("1000.00");
            assertThat(balance.unconvertedCurrencies()).containsExactly("JPY");
            assertThat(balance.accounts()).extracting(AccountSummary::name).containsExactly("CIB Account", "Yen wallet");
            assertThat(balance.accounts().get(1).balanceInBase()).isNull();
        }

        @Test
        void negativeBalancesAreKept() {
            when(dashboardRepository.accountBalances(USER_ID, NOW)).thenReturn(List.of(
                    new AccountBalanceRow(cib, "Credit card", "card", "EGP", "1111", d("-250.00"))));

            assertThat(service.getDashboard(USER_ID, null, 3).balance().total()).hasToString("-250.00");
        }

        @Test
        void conversionRoundsHalvesAwayFromZeroLikePostgres() {
            when(dashboardRepository.accountBalances(USER_ID, NOW)).thenReturn(List.of(
                    new AccountBalanceRow(usd, "USD", "e_wallet", "USD", null, d("0.01"))));
            when(fxRateService.rate("USD", "EGP", NOW)).thenReturn(Optional.of(d("0.5")));

            assertThat(service.getDashboard(USER_ID, null, 3).balance().total()).hasToString("0.01");
        }
    }

    @Nested
    class Budget {

        private final UUID budgetId = UUID.randomUUID();

        private BudgetRow budget(String amount, boolean rollover, String start) {
            return new BudgetRow(budgetId, d(amount), LocalDate.parse(start), rollover, 80);
        }

        @Test
        void absentWhenNoBudgetIsSet() {
            assertThat(service.getDashboard(USER_ID, null, 3).budget()).isNull();
        }

        @Test
        void onTrackMatchesTheDesign() {
            when(dashboardRepository.overallMonthlyBudget(USER_ID, LocalDate.of(2026, 11, 1)))
                    .thenReturn(Optional.of(budget("18000.00", false, "2026-10-01")));

            BudgetSummary budget = service.getDashboard(USER_ID, null, 3).budget();

            assertThat(budget.amount()).hasToString("18000.00");
            assertThat(budget.limit()).hasToString("18000.00");
            assertThat(budget.carriedOver()).hasToString("0.00");
            assertThat(budget.spent()).hasToString("12450.00");
            assertThat(budget.remaining()).hasToString("5550.00");
            assertThat(budget.usedPercent()).isEqualTo(69);
            assertThat(budget.status()).isEqualTo("ON_TRACK");
            assertThat(budget.alertThresholdPct()).isEqualTo(80);
            verify(dashboardRepository, never()).monthlyExpenses(any(), any(), any(), any());
        }

        @Test
        void nearLimitFromTheAlertThresholdAndAtExactly100Percent() {
            BudgetRow row = budget("1000.00", false, "2026-11-01");
            assertThat(service.budget(row, USER_ID, CAIRO, YearMonth.of(2026, 11), d("799.99")).status())
                    .isEqualTo("ON_TRACK");
            assertThat(service.budget(row, USER_ID, CAIRO, YearMonth.of(2026, 11), d("800.00")).status())
                    .isEqualTo("NEAR_LIMIT");
            BudgetSummary full = service.budget(row, USER_ID, CAIRO, YearMonth.of(2026, 11), d("1000.00"));
            assertThat(full.status()).isEqualTo("NEAR_LIMIT");
            assertThat(full.usedPercent()).isEqualTo(100);
            assertThat(full.remaining()).hasToString("0.00");
        }

        @Test
        void overBudgetHasNegativeRemaining() {
            BudgetSummary over = service.budget(budget("18000.00", false, "2026-10-01"), USER_ID, CAIRO,
                    YearMonth.of(2026, 10), d("31410.00"));

            assertThat(over.status()).isEqualTo("OVER");
            assertThat(over.remaining()).hasToString("-13410.00");
            assertThat(over.usedPercent()).isEqualTo(174);
        }

        @Test
        void rolloverCarriesUnspentAmountsButNeverOverspending() {
            BudgetRow row = budget("1000.00", true, "2026-08-01");
            // Aug: spent 600 -> carry 400. Sep: limit 1400, spent 1500 -> carry 0. Oct: limit 1000, spent 700 -> 300.
            when(dashboardRepository.monthlyExpenses(USER_ID, CAIRO,
                    YearMonth.of(2026, 8).atDay(1).atStartOfDay(CAIRO).toInstant(),
                    YearMonth.of(2026, 11).atDay(1).atStartOfDay(CAIRO).toInstant()))
                    .thenReturn(Map.of(YearMonth.of(2026, 8), d("600.00"),
                            YearMonth.of(2026, 9), d("1500.00"),
                            YearMonth.of(2026, 10), d("700.00")));

            BudgetSummary november = service.budget(row, USER_ID, CAIRO, YearMonth.of(2026, 11), d("650.00"));

            assertThat(november.carriedOver()).hasToString("300.00");
            assertThat(november.limit()).hasToString("1300.00");
            assertThat(november.remaining()).hasToString("650.00");
            assertThat(november.usedPercent()).isEqualTo(50);
            assertThat(november.rollover()).isTrue();
        }

        @Test
        void rolloverInItsFirstMonthCarriesNothing() {
            BudgetSummary first = service.budget(budget("1000.00", true, "2026-11-01"), USER_ID, CAIRO,
                    YearMonth.of(2026, 11), d("100.00"));

            assertThat(first.carriedOver()).hasToString("0.00");
            verify(dashboardRepository, never()).monthlyExpenses(any(), any(), any(), any());
        }
    }

    @Nested
    class Recent {

        private final UUID cib = UUID.randomUUID();
        private final UUID cash = UUID.randomUUID();
        private final UUID groceries = UUID.randomUUID();

        private RecentTransactionRow row(String type, String amount, String currency, String fx, String merchant,
                                         String categoryName, String categoryKey, UUID counterpart,
                                         String counterpartName) {
            return new RecentTransactionRow(UUID.randomUUID(), type, d(amount), currency, d(fx),
                    Instant.parse("2026-11-19T12:32:00Z"), merchant, null,
                    categoryKey == null ? null : groceries, categoryName, categoryKey,
                    cib, "CIB Account", counterpart, counterpartName);
        }

        @Test
        void mapsExpenseIncomeAndTransfer() {
            when(dashboardRepository.recentTransactions(USER_ID, NOW, 3)).thenReturn(List.of(
                    row("expense", "850.00", "EGP", "1", "Carrefour", "Groceries", "groceries", null, null),
                    row("income", "350.00", "USD", "48.2", null, "Freelance", "freelance", null, null),
                    row("transfer_out", "4000.00", "EGP", "1", null, null, null, cash, "Cash")));

            List<RecentTransaction> recent = service.getDashboard(USER_ID, null, 3).recentTransactions();

            RecentTransaction expense = recent.get(0);
            assertThat(expense.type()).isEqualTo("EXPENSE");
            assertThat(expense.title()).isEqualTo("Carrefour");
            assertThat(expense.amount()).hasToString("850.00");
            assertThat(expense.signedAmount()).hasToString("-850.00");
            assertThat(expense.category().key()).isEqualTo("groceries");
            assertThat(expense.account().name()).isEqualTo("CIB Account");
            assertThat(expense.toAccount()).isNull();
            // 12:32 UTC is 14:32 in Cairo on 19 Nov.
            assertThat(expense.date()).isEqualTo(LocalDate.of(2026, 11, 19));
            assertThat(expense.time()).isEqualTo("14:32");

            RecentTransaction income = recent.get(1);
            assertThat(income.type()).isEqualTo("INCOME");
            assertThat(income.title()).isEqualTo("Freelance");   // no merchant: category name
            assertThat(income.signedAmount()).hasToString("350.00");
            assertThat(income.currency()).isEqualTo("USD");
            assertThat(income.amountInBase()).hasToString("16870.00");

            RecentTransaction transfer = recent.get(2);
            assertThat(transfer.type()).isEqualTo("TRANSFER");
            assertThat(transfer.title()).isEqualTo("Transfer to Cash");
            assertThat(transfer.signedAmount()).isNull();
            assertThat(transfer.category()).isNull();
            assertThat(transfer.toAccount().name()).isEqualTo("Cash");
        }

        @Test
        void passesTheRequestedLimit() {
            service.getDashboard(USER_ID, null, 20);

            verify(dashboardRepository).recentTransactions(USER_ID, NOW, 20);
        }
    }

    private static void assertInvalid(Runnable call, String field) {
        assertThatThrownBy(call::run).isInstanceOfSatisfying(ApiException.class, e -> {
            assertThat(e.getErrorCode()).isEqualTo(ErrorCode.VALIDATION_FAILED);
            assertThat(e.getFieldErrors()).extracting("field").containsExactly(field);
        });
    }
}
