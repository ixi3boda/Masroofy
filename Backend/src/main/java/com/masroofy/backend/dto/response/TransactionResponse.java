package com.masroofy.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonFormat;
import com.fasterxml.jackson.annotation.JsonInclude;
import com.masroofy.backend.dto.response.DashboardResponse.AccountRef;
import com.masroofy.backend.dto.response.DashboardResponse.CategoryRef;
import io.swagger.v3.oas.annotations.media.Schema;
import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.util.UUID;

/**
 * One income or expense. The same fields, names and meaning as the dashboard's recent transactions, so the app maps
 * both the same way. Money is a string with two decimals.
 */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record TransactionResponse(
        UUID id,
        @Schema(example = "EXPENSE", allowableValues = {"EXPENSE", "INCOME"}) String type,
        @Schema(example = "Carrefour", description = "Merchant, else the category name") String title,
        @Schema(example = "Carrefour") String merchant,
        String note,
        CategoryRef category,
        AccountRef account,
        @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"850.00\"",
                description = "Always positive, in `currency`")
        BigDecimal amount,
        @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"-850.00\"",
                description = "Negative for expenses, positive for income")
        BigDecimal signedAmount,
        @Schema(example = "EGP") String currency,
        @JsonFormat(shape = JsonFormat.Shape.STRING) @Schema(implementation = String.class, format = "decimal", example = "\"850.00\"",
                description = "In the user's base currency, with the rate stored on the transaction")
        BigDecimal amountInBase,
        @Schema(description = "Local date in the user's time zone") LocalDate date,
        @Schema(example = "11:51", description = "Local time in the user's time zone") String time,
        Instant occurredAt,
        @Schema(example = "manual") String source,
        @Schema(example = "confirmed", allowableValues = {"confirmed", "pending_review"}) String status,
        Instant createdAt) {
}
