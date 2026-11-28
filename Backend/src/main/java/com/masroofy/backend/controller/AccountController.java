package com.masroofy.backend.controller;

import com.masroofy.backend.config.OpenApiConfig;
import com.masroofy.backend.dto.response.AccountResponse;
import com.masroofy.backend.exception.ErrorResponse;
import com.masroofy.backend.security.AuthenticatedUser;
import com.masroofy.backend.service.AccountService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import java.util.List;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/accounts")
@Tag(name = "Accounts")
@SecurityRequirement(name = OpenApiConfig.BEARER_AUTH)
@ApiResponse(responseCode = "401", description = "Missing, invalid or revoked token",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "403", description = "EMAIL_NOT_VERIFIED or ACCOUNT_DISABLED",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
public class AccountController {

    private final AccountService accountService;

    public AccountController(AccountService accountService) {
        this.accountService = accountService;
    }

    @Operation(summary = "The user's open accounts",
            description = "For the account picker on Add Transaction. Oldest first; the first one is the default.")
    @ApiResponse(responseCode = "200", description = "The accounts (can be empty)")
    @GetMapping
    public List<AccountResponse> list(@AuthenticationPrincipal AuthenticatedUser user) {
        return accountService.listAccounts(user.userId());
    }
}
