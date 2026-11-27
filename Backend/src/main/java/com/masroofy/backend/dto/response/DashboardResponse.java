package com.masroofy.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.List;
import java.util.UUID;

/**
 * Everything the "02 / Home Dashboard" screen shows, read from one database snapshot so every number agrees.
 * Money is a string with two decimals ("12450.00"); parse it with BigDecimal, never with a float.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record DashboardResponse(
        Period period,
        @Schema(example = "EGP") String baseCurrency,
        Summary summary,
        Balance balance,
        @Schema(description = "Absent when the user has no overall monthly budget") BudgetSummary budget,
        List<RecentTransaction> recentTransactions,
        Badges badges) {

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Period(
            @Schema(example = "2026-11") String month,
            @Schema(example = "Nov 2026") String label,
            LocalDate startDate,
            LocalDate endDate,
            @Schema(example = "Africa/Cairo") String timezone,
            @Schema(description = "Numbers are as of this moment: now for the current month, else the month's end")
            Instant asOf,
            boolean currentMonth) {
    }

    /** The "Total Salary" (total income) and "Total Expense" cards and the "Income vs Expenses" chart. */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Summary(
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"30000.00\"")
            BigDecimal totalIncome,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"12450.00\"")
            BigDecimal totalExpense,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"17550.00\"")
            BigDecimal net) {
    }

    /** "Current Balance" and the account cards. */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Balance(
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"39100.00\"",
                    description = "Sum of the accounts converted to the base currency")
            BigDecimal total,
            @Schema(description = "Largest balance (in base currency) first")
            List<AccountSummary> accounts,
            @Schema(description = "Currencies with no exchange rate; those accounts are left out of the total")
            List<String> unconvertedCurrencies) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record AccountSummary(
            UUID id,
            @Schema(example = "CIB Account") String name,
            @Schema(example = "bank", allowableValues = {"cash", "card", "bank", "e_wallet"}) String type,
            @Schema(example = "EGP") String currency,
            @Schema(example = "4821") String cardLast4,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"20550.00\"",
                    description = "In the account's own currency")
            BigDecimal balance,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"20550.00\"",
                    description = "Absent when no exchange rate is available")
            BigDecimal balanceInBase,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"48.500000\"",
                    description = "Base-currency units per 1 unit of the account currency; absent for the base currency")
            BigDecimal fxRate) {
    }

    /** "Budget Progress". Amounts are in the base currency. */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record BudgetSummary(
            UUID id,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"18000.00\"")
            BigDecimal amount,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"0.00\"",
                    description = "Unspent amount carried over from earlier months (rollover budgets only)")
            BigDecimal carriedOver,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"18000.00\"",
                    description = "amount + carriedOver: the limit for this month")
            BigDecimal limit,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"12450.00\"")
            BigDecimal spent,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"5550.00\"",
                    description = "Negative when over budget")
            BigDecimal remaining,
            @Schema(example = "69", description = "spent / limit, rounded down") int usedPercent,
            @Schema(example = "80") int alertThresholdPct,
            @Schema(example = "ON_TRACK", allowableValues = {"ON_TRACK", "NEAR_LIMIT", "OVER"}) String status,
            boolean rollover) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record RecentTransaction(
            UUID id,
            @Schema(example = "EXPENSE", allowableValues = {"EXPENSE", "INCOME", "TRANSFER"}) String type,
            @Schema(example = "Carrefour", description = "Merchant, else category name, else \"Transfer to …\"")
            String title,
            @Schema(example = "Carrefour") String merchant,
            String note,
            @Schema(description = "Absent for transfers") CategoryRef category,
            @Schema(description = "For a transfer: the account the money left") AccountRef account,
            @Schema(description = "Transfers only: the account the money went to") AccountRef toAccount,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"850.00\"",
                    description = "Always positive, in `currency`")
            BigDecimal amount,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"-850.00\"",
                    description = "Negative for expenses, positive for income; absent for transfers")
            BigDecimal signedAmount,
            @Schema(example = "EGP") String currency,
            @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"850.00\"")
            BigDecimal amountInBase,
            @Schema(description = "Local date in the user's time zone") LocalDate date,
            @Schema(example = "14:32", description = "Local time in the user's time zone") String time,
            Instant occurredAt) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record CategoryRef(
            UUID id,
            @Schema(example = "groceries", description = "Category key; the app maps it to an icon") String key,
            @Schema(example = "Groceries") String name) {
    }

    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record AccountRef(UUID id, @Schema(example = "CIB Account") String name) {
    }

    /** Red dots on the dashboard. */
    @JsonInclude(JsonInclude.Include.NON_NULL)
    public record Badges(
            @Schema(example = "1", description = "Captured transactions (SMS, receipt, voice) waiting for review")
            long pendingReview) {
    }
}
