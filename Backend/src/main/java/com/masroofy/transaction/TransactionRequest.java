package com.masroofy.transaction;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.validation.constraints.DecimalMin;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Size;

import java.math.BigDecimal;
import java.time.LocalDate;
import java.time.LocalTime;

/**
 * Body of POST /api/transactions (add without voice) and PUT /api/transactions/{id} (edit).
 * Optional fields: transaction_type (expense), currency (EGP), category (other, or income for income),
 * date (today when adding, unchanged when editing), payment_method (unknown); merchant, time and note may be null.
 */
public record TransactionRequest(
        @Pattern(regexp = "expense|income", message = "must be expense or income")
        String transactionType,

        @NotNull(message = "is required")
        @DecimalMin(value = "0.01", message = "must be greater than 0")
        @Digits(integer = 12, fraction = 2, message = "must have at most 2 decimals")
        BigDecimal amount,

        @Pattern(regexp = "[A-Za-z]{3}", message = "must be a 3-letter currency code such as EGP")
        String currency,

        @Size(max = 120, message = "must be at most 120 characters")
        String merchant,

        String category,

        LocalDate date,

        @JsonFormat(pattern = "HH:mm")
        LocalTime time,

        @Pattern(regexp = "cash|card|wallet|unknown", message = "must be cash, card, wallet or unknown")
        String paymentMethod,

        @Size(max = 500, message = "must be at most 500 characters")
        String note) {
}
