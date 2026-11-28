package com.masroofy.backend.dto.response;

import com.fasterxml.jackson.annotation.JsonInclude;
import com.masroofy.backend.model.Account;
import io.swagger.v3.oas.annotations.media.Schema;
import java.util.UUID;

/** An account the user can record a transaction against. */
@JsonInclude(JsonInclude.Include.NON_NULL)
public record AccountResponse(
        UUID id,
        @Schema(example = "CIB Account") String name,
        @Schema(example = "bank", allowableValues = {"cash", "card", "bank", "e_wallet"}) String type,
        @Schema(example = "EGP") String currency,
        @Schema(example = "4821", description = "Absent when the account has no card") String cardLast4) {

    public static AccountResponse from(Account account) {
        return new AccountResponse(account.id(), account.name(), account.type(), account.currency(),
                account.cardLast4());
    }
}
