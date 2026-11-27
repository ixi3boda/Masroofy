package com.masroofy.backend.controller;

import com.masroofy.backend.config.OpenApiConfig;
import com.masroofy.backend.dto.response.DashboardResponse;
import com.masroofy.backend.exception.ErrorResponse;
import com.masroofy.backend.security.AuthenticatedUser;
import com.masroofy.backend.service.DashboardService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.Parameter;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/dashboard")
@Tag(name = "Dashboard", description = "Home screen (Figma 02 / Home Dashboard)")
@SecurityRequirement(name = OpenApiConfig.BEARER_AUTH)
@ApiResponse(responseCode = "400", description = "VALIDATION_FAILED: bad month or recentLimit",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "401", description = "Missing, invalid or revoked token",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "403", description = "EMAIL_NOT_VERIFIED or ACCOUNT_DISABLED",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
public class DashboardController {

    private final DashboardService dashboardService;

    public DashboardController(DashboardService dashboardService) {
        this.dashboardService = dashboardService;
    }

    @Operation(summary = "Home dashboard for one month",
            description = "Income, expenses, balances, budget progress, recent transactions and badges, all from one "
                    + "consistent snapshot. Only confirmed, non-deleted transactions count; transfers are neither "
                    + "income nor expense. Money is a string with two decimals; totals are in `baseCurrency`.")
    @ApiResponse(responseCode = "200", description = "The dashboard")
    @GetMapping
    public DashboardResponse dashboard(
            @AuthenticationPrincipal AuthenticatedUser user,
            @Parameter(description = "Month in the user's time zone, YYYY-MM. Defaults to the current month; "
                    + "cannot be in the future.", example = "2026-10")
            @RequestParam(required = false) String month,
            @Parameter(description = "How many recent transactions to return, 1-20", example = "3")
            @RequestParam(defaultValue = "" + DashboardService.DEFAULT_RECENT_LIMIT) int recentLimit) {
        return dashboardService.getDashboard(user.userId(), month, recentLimit);
    }
}
