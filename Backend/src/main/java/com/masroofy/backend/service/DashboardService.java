package com.masroofy.backend.service;

import com.masroofy.backend.dto.response.DashboardResponse;
import com.masroofy.backend.dto.response.DashboardResponse.AccountRef;
import com.masroofy.backend.dto.response.DashboardResponse.AccountSummary;
import com.masroofy.backend.dto.response.DashboardResponse.Badges;
import com.masroofy.backend.dto.response.DashboardResponse.Balance;
import com.masroofy.backend.dto.response.DashboardResponse.BudgetSummary;
import com.masroofy.backend.dto.response.DashboardResponse.CategoryRef;
import com.masroofy.backend.dto.response.DashboardResponse.Period;
import com.masroofy.backend.dto.response.DashboardResponse.RecentTransaction;
import com.masroofy.backend.dto.response.DashboardResponse.Summary;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.DashboardRepository;
import com.masroofy.backend.repository.DashboardRepository.AccountBalanceRow;
import com.masroofy.backend.repository.DashboardRepository.BudgetRow;
import com.masroofy.backend.repository.DashboardRepository.MonthTotals;
import com.masroofy.backend.repository.DashboardRepository.RecentTransactionRow;
import com.masroofy.backend.repository.UserRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.Clock;
import java.time.DateTimeException;
import java.time.Instant;
import java.time.YearMonth;
import java.time.ZoneId;
import java.time.ZoneOffset;
import java.time.ZonedDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.TransactionDefinition;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Builds the home dashboard. All queries run in one read-only REPEATABLE READ transaction, so the cards, the budget
 * and the chart are computed from the same snapshot and always agree with each other.
 *
 * <p>Rules: only confirmed, non-deleted transactions count; transfers are neither income nor expense; "this month"
 * uses the user's time zone; totals are in the user's base currency using each transaction's own fx_rate_to_base;
 * account balances are converted with the latest exchange rate at {@code asOf}.
 */
@Service
public class DashboardService {

    public static final int DEFAULT_RECENT_LIMIT = 3;
    public static final int MAX_RECENT_LIMIT = 20;
    static final YearMonth OLDEST_MONTH = YearMonth.of(2000, 1);
    /** Upper bound on the months a rollover budget is replayed over (20 years). */
    static final int MAX_ROLLOVER_MONTHS = 240;

    private static final DateTimeFormatter LABEL = DateTimeFormatter.ofPattern("MMM yyyy", Locale.ENGLISH);
    private static final DateTimeFormatter TIME = DateTimeFormatter.ofPattern("HH:mm");
    private static final int MONEY_SCALE = 2;
    private static final int DISPLAY_RATE_SCALE = 6;
    private static final BigDecimal HUNDRED = BigDecimal.valueOf(100);
    private static final BigDecimal MAX_PERCENT = BigDecimal.valueOf(999_999);

    private final UserRepository userRepository;
    private final DashboardRepository dashboardRepository;
    private final FxRateService fxRateService;
    private final TransactionTemplate snapshot;
    private final Clock clock;

    public DashboardService(UserRepository userRepository, DashboardRepository dashboardRepository,
                            FxRateService fxRateService, PlatformTransactionManager transactionManager, Clock clock) {
        this.userRepository = userRepository;
        this.dashboardRepository = dashboardRepository;
        this.fxRateService = fxRateService;
        this.clock = clock;
        this.snapshot = new TransactionTemplate(transactionManager);
        this.snapshot.setIsolationLevel(TransactionDefinition.ISOLATION_REPEATABLE_READ);
        this.snapshot.setReadOnly(true);
    }

    /**
     * @param month       "YYYY-MM" in the user's time zone; null for the current month
     * @param recentLimit how many recent transactions to return (1 to {@value #MAX_RECENT_LIMIT})
     */
    public DashboardResponse getDashboard(UUID userId, String month, int recentLimit) {
        if (recentLimit < 1 || recentLimit > MAX_RECENT_LIMIT) {
            throw invalid("recentLimit", "Must be between 1 and " + MAX_RECENT_LIMIT);
        }
        User user = userRepository.findById(userId).orElseThrow(() -> new ApiException(ErrorCode.USER_NOT_FOUND));
        ZoneId zone = zoneOf(user.timezone());
        Instant now = clock.instant();
        YearMonth currentMonth = YearMonth.from(now.atZone(zone));
        YearMonth target = parseMonth(month, currentMonth);

        Instant from = target.atDay(1).atStartOfDay(zone).toInstant();
        Instant monthEnd = target.plusMonths(1).atDay(1).atStartOfDay(zone).toInstant();
        Instant asOf = now.isBefore(monthEnd) ? now : monthEnd;
        Period period = new Period(target.toString(), LABEL.format(target), target.atDay(1), target.atEndOfMonth(),
                zone.getId(), asOf, target.equals(currentMonth));

        return snapshot.execute(status -> build(user, zone, period, from, asOf, recentLimit));
    }

    private DashboardResponse build(User user, ZoneId zone, Period period, Instant from, Instant asOf,
                                    int recentLimit) {
        UUID userId = user.id();
        String base = user.baseCurrency();

        MonthTotals totals = dashboardRepository.monthTotals(userId, from, asOf);
        BigDecimal income = money(totals.income());
        BigDecimal expense = money(totals.expense());
        Summary summary = new Summary(income, expense, income.subtract(expense));

        Balance balance = balance(dashboardRepository.accountBalances(userId, asOf), base, asOf);
        BudgetSummary budget = dashboardRepository.overallMonthlyBudget(userId, period.startDate())
                .map(row -> budget(row, userId, zone, YearMonth.parse(period.month()), expense))
                .orElse(null);
        List<RecentTransaction> recent = dashboardRepository.recentTransactions(userId, asOf, recentLimit).stream()
                .map(row -> recentTransaction(row, zone))
                .toList();
        Badges badges = new Badges(dashboardRepository.pendingReviewCount(userId));

        return new DashboardResponse(period, base, summary, balance, budget, recent, badges);
    }

    // ---- Balance -------------------------------------------------------------------------------------------------

    private Balance balance(List<AccountBalanceRow> rows, String base, Instant asOf) {
        Map<String, Optional<BigDecimal>> rates = new HashMap<>();
        List<AccountSummary> accounts = new ArrayList<>();
        List<String> unconverted = new ArrayList<>();
        BigDecimal total = BigDecimal.ZERO;

        for (AccountBalanceRow row : rows) {
            BigDecimal accountBalance = money(row.balance());
            Optional<BigDecimal> rate = rates.computeIfAbsent(row.currency(),
                    currency -> fxRateService.rate(currency, base, asOf));
            BigDecimal inBase = rate.map(r -> money(accountBalance.multiply(r))).orElse(null);
            BigDecimal shownRate = row.currency().equals(base) || rate.isEmpty()
                    ? null
                    : rate.get().setScale(DISPLAY_RATE_SCALE, RoundingMode.HALF_EVEN);
            if (inBase == null) {
                if (!unconverted.contains(row.currency())) {
                    unconverted.add(row.currency());
                }
            } else {
                total = total.add(inBase);
            }
            accounts.add(new AccountSummary(row.id(), row.name(), row.type(), row.currency(), row.cardLast4(),
                    accountBalance, inBase, shownRate));
        }

        // Largest balance first (as on the screen); accounts that cannot be converted go last.
        accounts.sort(Comparator
                .comparing((AccountSummary a) -> a.balanceInBase() == null)
                .thenComparing(AccountSummary::balanceInBase, Comparator.nullsLast(Comparator.reverseOrder()))
                .thenComparing(AccountSummary::name));
        return new Balance(money(total), accounts, unconverted);
    }

    // ---- Budget --------------------------------------------------------------------------------------------------

    /**
     * Budget for {@code month}. With rollover, each earlier month's unspent amount (never a negative one) is added
     * to the next month's limit, starting from the budget's first month.
     */
    BudgetSummary budget(BudgetRow row, UUID userId, ZoneId zone, YearMonth month, BigDecimal spent) {
        BigDecimal amount = money(row.amount());
        BigDecimal carriedOver = BigDecimal.ZERO;

        YearMonth firstMonth = YearMonth.from(row.startDate());
        if (row.rollover() && firstMonth.isBefore(month)) {
            YearMonth replayFrom = month.minusMonths(MAX_ROLLOVER_MONTHS).isAfter(firstMonth)
                    ? month.minusMonths(MAX_ROLLOVER_MONTHS) : firstMonth;
            Map<YearMonth, BigDecimal> spentByMonth = dashboardRepository.monthlyExpenses(userId, zone,
                    replayFrom.atDay(1).atStartOfDay(zone).toInstant(),
                    month.atDay(1).atStartOfDay(zone).toInstant());
            for (YearMonth m = replayFrom; m.isBefore(month); m = m.plusMonths(1)) {
                BigDecimal monthLimit = amount.add(carriedOver);
                BigDecimal unspent = monthLimit.subtract(spentByMonth.getOrDefault(m, BigDecimal.ZERO));
                carriedOver = unspent.signum() > 0 ? unspent : BigDecimal.ZERO;
            }
        }

        BigDecimal limit = money(amount.add(carriedOver));
        BigDecimal remaining = limit.subtract(spent);
        int usedPercent = spent.multiply(HUNDRED).divide(limit, 0, RoundingMode.DOWN)
                .min(MAX_PERCENT).max(BigDecimal.ZERO).intValueExact();
        String status;
        if (spent.compareTo(limit) > 0) {
            status = "OVER";
        } else if (usedPercent >= row.alertThresholdPct()) {
            status = "NEAR_LIMIT";
        } else {
            status = "ON_TRACK";
        }
        return new BudgetSummary(row.id(), amount, money(carriedOver), limit, spent, money(remaining), usedPercent,
                row.alertThresholdPct(), status, row.rollover());
    }

    // ---- Recent transactions -------------------------------------------------------------------------------------

    private RecentTransaction recentTransaction(RecentTransactionRow row, ZoneId zone) {
        BigDecimal amount = money(row.amount());
        BigDecimal inBase = money(row.amount().multiply(row.fxRateToBase()));
        ZonedDateTime local = row.occurredAt().atZone(zone);
        AccountRef account = new AccountRef(row.accountId(), row.accountName());

        String type;
        String title;
        BigDecimal signed;
        CategoryRef category = null;
        AccountRef toAccount = null;
        switch (row.type()) {
            case "income", "expense" -> {
                type = row.type().equals("income") ? "INCOME" : "EXPENSE";
                signed = type.equals("INCOME") ? amount : amount.negate();
                category = new CategoryRef(row.categoryId(), row.categoryKey(), row.categoryName());
                title = hasText(row.merchant()) ? row.merchant() : row.categoryName();
            }
            case "transfer_out" -> {
                type = "TRANSFER";
                signed = null;
                toAccount = row.counterpartAccountId() == null
                        ? null : new AccountRef(row.counterpartAccountId(), row.counterpartAccountName());
                title = toAccount == null ? "Transfer" : "Transfer to " + toAccount.name();
            }
            default -> throw new IllegalStateException("Unexpected transaction type " + row.type());
        }
        return new RecentTransaction(row.id(), type, title, row.merchant(), row.note(), category, account, toAccount,
                amount, signed, row.currency(), inBase, local.toLocalDate(), TIME.format(local), row.occurredAt());
    }

    // ---- Helpers -------------------------------------------------------------------------------------------------

    private static YearMonth parseMonth(String month, YearMonth currentMonth) {
        if (month == null || month.isBlank()) {
            return currentMonth;
        }
        YearMonth parsed;
        try {
            parsed = YearMonth.parse(month.trim());
        } catch (DateTimeParseException e) {
            throw invalid("month", "Use the format YYYY-MM, e.g. 2026-10");
        }
        if (parsed.isAfter(currentMonth)) {
            throw invalid("month", "Cannot be in the future");
        }
        if (parsed.isBefore(OLDEST_MONTH)) {
            throw invalid("month", "Must be " + OLDEST_MONTH + " or later");
        }
        return parsed;
    }

    /** The user's IANA time zone; UTC if it is missing or unknown. */
    static ZoneId zoneOf(String timezone) {
        if (timezone == null || timezone.isBlank()) {
            return ZoneOffset.UTC;
        }
        try {
            return ZoneId.of(timezone);
        } catch (DateTimeException e) {
            return ZoneOffset.UTC;
        }
    }

    /** Two decimals, ties away from zero: the same rule as PostgreSQL's ROUND, so Java and SQL amounts agree. */
    static BigDecimal money(BigDecimal value) {
        return (value == null ? BigDecimal.ZERO : value).setScale(MONEY_SCALE, RoundingMode.HALF_UP);
    }

    private static boolean hasText(String value) {
        return value != null && !value.isBlank();
    }

    private static ApiException invalid(String field, String message) {
        return new ApiException(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(), Map.of(),
                List.of(new FieldErrorDetail(field, "Invalid", message)), null);
    }
}
