package com.masroofy.backend.controller;

import com.masroofy.backend.config.OpenApiConfig;
import com.masroofy.backend.dto.request.CreateTransactionRequest;
import com.masroofy.backend.dto.response.TransactionResponse;
import com.masroofy.backend.exception.ErrorResponse;
import com.masroofy.backend.security.AuthenticatedUser;
import com.masroofy.backend.service.TransactionService;
import com.masroofy.backend.service.TransactionService.CreateResult;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import java.net.URI;
import java.util.UUID;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/transactions")
@Tag(name = "Transactions", description = "Add Expense / Add Income (Figma 03-06 → 03-14)")
@SecurityRequirement(name = OpenApiConfig.BEARER_AUTH)
@ApiResponse(responseCode = "400", description = "VALIDATION_FAILED or MALFORMED_REQUEST",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "401", description = "Missing, invalid or revoked token",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "403", description = "EMAIL_NOT_VERIFIED or ACCOUNT_DISABLED",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
public class TransactionController {

    private final TransactionService transactionService;

    public TransactionController(TransactionService transactionService) {
        this.transactionService = transactionService;
    }

    @Operation(summary = "Add an expense or an income",
            description = "Saves a confirmed, manual transaction. The amount is positive; `type` gives the direction. "
                    + "A date without `time` is stored as now (today) or midday in the user's time zone (earlier "
                    + "days). Sending the same `clientRequestId` again returns the first transaction (200) instead "
                    + "of saving it twice.")
    @ApiResponse(responseCode = "201", description = "Saved")
    @ApiResponse(responseCode = "200", description = "Already saved by an earlier request with this clientRequestId")
    @ApiResponse(responseCode = "409", description = "IDEMPOTENCY_KEY_REUSED: clientRequestId used for a different transaction",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @ApiResponse(responseCode = "422", description = "FX_RATE_UNAVAILABLE: no exchange rate for the account's currency",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping
    public ResponseEntity<TransactionResponse> create(@AuthenticationPrincipal AuthenticatedUser user,
                                                      @Valid @RequestBody CreateTransactionRequest request) {
        CreateResult result = transactionService.create(user.userId(), request);
        if (!result.created()) {
            return ResponseEntity.ok(result.transaction());
        }
        return ResponseEntity.created(URI.create("/api/v1/transactions/" + result.transaction().id()))
                .body(result.transaction());
    }

    @Operation(summary = "Get one of the user's transactions")
    @ApiResponse(responseCode = "200", description = "The transaction")
    @ApiResponse(responseCode = "404", description = "NOT_FOUND: no such transaction for this user",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @GetMapping("/{id}")
    public TransactionResponse get(@AuthenticationPrincipal AuthenticatedUser user, @PathVariable UUID id) {
        return transactionService.get(user.userId(), id);
    }
}
