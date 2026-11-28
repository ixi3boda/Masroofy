package com.masroofy.backend.dto.request;

import io.swagger.v3.oas.annotations.media.Schema;
import jakarta.validation.constraints.Digits;
import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import jakarta.validation.constraints.Pattern;
import jakarta.validation.constraints.Positive;
import jakarta.validation.constraints.Size;
import java.math.BigDecimal;
import java.time.LocalDate;
import java.util.UUID;

/**
 * Screens 03-06 → 03-14 "Add Expense" / "Add Income". Format rules only; the service checks the rest (date not in
 * the future, account and category of this user, category kind).
 */
public record CreateTransactionRequest(
        @Schema(description = "Made by the app once per draft and sent again on Retry, so a retry never saves twice",
                example = "6f1c0b9e-3d1a-4a57-9d55-0d3c2c8f4a10")
        @NotNull(message = "Is required")
        UUID clientRequestId,

        @Schema(example = "EXPENSE", allowableValues = {"EXPENSE", "INCOME"})
        @NotNull(message = "Choose expense or income")
        @Pattern(regexp = "EXPENSE|INCOME", message = "Must be EXPENSE or INCOME")
        String type,

        @Schema(type = "string", format = "decimal", example = "850.00", description = "Positive, at most 2 decimals")
        @NotNull(message = "Enter an amount")
        @Positive(message = "Enter an amount greater than 0")
        @Digits(integer = 12, fraction = 2, message = "Use at most 12 digits and 2 decimals")
        BigDecimal amount,

        @Schema(example = "Carrefour", description = "Merchant of an expense, or the title of an income")
        @NotBlank(message = "Enter a title")
        @Size(max = 120, message = "Must be at most 120 characters")
        String title,

        @Schema(example = "groceries", description = "The app's category key. Send this or categoryId, not both")
        @Size(max = 40, message = "Must be at most 40 characters")
        String categoryKey,

        @Schema(description = "A category id. Send this or categoryKey, not both")
        UUID categoryId,

        @Schema(example = "2026-11-26", description = "Local date in the user's time zone; not in the future")
        @NotNull(message = "Choose a date")
        LocalDate date,

        @Schema(example = "11:51", description = "Optional local time HH:mm (24 h) in the user's time zone")
        @Pattern(regexp = "([01]\\d|2[0-3]):[0-5]\\d", message = "Use the format HH:mm, e.g. 14:30")
        String time,

        @NotNull(message = "Choose an account")
        UUID accountId,

        @Schema(example = "Weekly groceries")
        @Size(max = 1000, message = "Must be at most 1000 characters")
        String note) {
}
