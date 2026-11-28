package com.masroofy.transaction;

import java.math.BigDecimal;
import java.util.List;

/** GET /api/transactions/summary?month=2026-11 — totals per currency, expenses broken down by category. */
public record MonthlySummary(String month, List<CurrencyTotals> currencies) {

    public record CurrencyTotals(String currency, BigDecimal totalExpense, BigDecimal totalIncome, BigDecimal net,
                                 long transactions, List<CategoryTotal> expensesByCategory) {
    }

    public record CategoryTotal(String category, BigDecimal total, long transactions) {
    }
}
