package com.masroofy.backend.controller;

import com.masroofy.backend.config.OpenApiConfig;
import com.masroofy.backend.dto.response.UserResponse;
import com.masroofy.backend.exception.ErrorResponse;
import com.masroofy.backend.security.AuthenticatedUser;
import com.masroofy.backend.service.UserService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/users")
@Tag(name = "Users")
@SecurityRequirement(name = OpenApiConfig.BEARER_AUTH)
@ApiResponse(responseCode = "401", description = "Missing, invalid or revoked token",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "403", description = "EMAIL_NOT_VERIFIED or ACCOUNT_DISABLED",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
public class UserController {

    private final UserService userService;

    public UserController(UserService userService) {
        this.userService = userService;
    }

    @Operation(summary = "Get the signed-in user's profile")
    @ApiResponse(responseCode = "200", description = "The profile")
    @GetMapping("/me")
    public UserResponse me(@AuthenticationPrincipal AuthenticatedUser user) {
        return userService.getUser(user.userId());
    }
}
