package com.masroofy.backend.controller;

import com.masroofy.backend.config.OpenApiConfig;
import com.masroofy.backend.dto.request.EmailRequest;
import com.masroofy.backend.dto.request.LoginRequest;
import com.masroofy.backend.dto.request.RefreshTokenRequest;
import com.masroofy.backend.dto.request.RegisterRequest;
import com.masroofy.backend.dto.request.ResetPasswordRequest;
import com.masroofy.backend.dto.request.VerifyCodeRequest;
import com.masroofy.backend.dto.response.AuthTokensResponse;
import com.masroofy.backend.dto.response.CodeDispatchResponse;
import com.masroofy.backend.dto.response.EmailVerifiedResponse;
import com.masroofy.backend.dto.response.MessageResponse;
import com.masroofy.backend.dto.response.RegisterResponse;
import com.masroofy.backend.dto.response.ResetCodeVerifiedResponse;
import com.masroofy.backend.exception.ErrorResponse;
import com.masroofy.backend.security.AuthenticatedUser;
import com.masroofy.backend.service.AuthService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.media.Content;
import io.swagger.v3.oas.annotations.media.Schema;
import io.swagger.v3.oas.annotations.responses.ApiResponse;
import io.swagger.v3.oas.annotations.security.SecurityRequirement;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

@RestController
@RequestMapping("/api/v1/auth")
@Tag(name = "Authentication", description = "Sign-up, email verification, login, tokens and password reset")
@ApiResponse(responseCode = "400", description = "Validation or business rule error",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "429", description = "RESEND_COOLDOWN, TOO_MANY_ATTEMPTS or RATE_LIMITED",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
@ApiResponse(responseCode = "503", description = "Firebase or email temporarily unavailable",
        content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
public class AuthController {

    private final AuthService authService;

    public AuthController(AuthService authService) {
        this.authService = authService;
    }

    @Operation(summary = "Create an account (screen 01-02)",
            description = "Creates the Firebase user and the profile, then emails a 6-digit verification code. "
                    + "409 EMAIL_ALREADY_IN_USE when the email already has an account.")
    @ApiResponse(responseCode = "201", description = "Account created; go to 01-03")
    @ApiResponse(responseCode = "409", description = "EMAIL_ALREADY_IN_USE",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/register")
    public ResponseEntity<RegisterResponse> register(@Valid @RequestBody RegisterRequest request) {
        return ResponseEntity.status(HttpStatus.CREATED).body(authService.register(request));
    }

    @Operation(summary = "Verify signup email (screen 01-03)",
            description = "400 INVALID_CODE (details.remainingAttempts) or INVALID_OR_EXPIRED_CODE; "
                    + "429 TOO_MANY_ATTEMPTS; 409 EMAIL_ALREADY_VERIFIED.")
    @ApiResponse(responseCode = "200", description = "Email verified; go to log in")
    @ApiResponse(responseCode = "409", description = "EMAIL_ALREADY_VERIFIED",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/email-verification/verify")
    public EmailVerifiedResponse verifyEmail(@Valid @RequestBody VerifyCodeRequest request) {
        return authService.verifyEmail(request);
    }

    @Operation(summary = "Resend the verification code (screen 01-03)",
            description = "Answers 202 the same way for unknown or already verified emails. "
                    + "429 RESEND_COOLDOWN with a Retry-After header when asked again too soon.")
    @ApiResponse(responseCode = "202", description = "Code sent")
    @PostMapping("/email-verification/resend")
    public ResponseEntity<CodeDispatchResponse> resendVerificationCode(@Valid @RequestBody EmailRequest request) {
        return ResponseEntity.accepted().body(authService.resendVerificationCode(request));
    }

    @Operation(summary = "Log in (screen 01-04)",
            description = "Returns Firebase tokens and the profile. 401 INVALID_CREDENTIALS; "
                    + "403 EMAIL_NOT_VERIFIED (details.maskedEmail, go to 01-03); 403 ACCOUNT_DISABLED.")
    @ApiResponse(responseCode = "200", description = "Logged in")
    @ApiResponse(responseCode = "401", description = "INVALID_CREDENTIALS",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @ApiResponse(responseCode = "403", description = "EMAIL_NOT_VERIFIED or ACCOUNT_DISABLED",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/login")
    public AuthTokensResponse login(@Valid @RequestBody LoginRequest request) {
        return authService.login(request);
    }

    @Operation(summary = "Refresh the access token",
            description = "401 INVALID_REFRESH_TOKEN means the user must log in again.")
    @ApiResponse(responseCode = "200", description = "New tokens")
    @ApiResponse(responseCode = "401", description = "INVALID_REFRESH_TOKEN",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/token/refresh")
    public AuthTokensResponse refresh(@Valid @RequestBody RefreshTokenRequest request) {
        return authService.refresh(request);
    }

    @Operation(summary = "Log out", description = "Revokes every refresh token of the user, on all devices.",
            security = @SecurityRequirement(name = OpenApiConfig.BEARER_AUTH))
    @ApiResponse(responseCode = "204", description = "Logged out")
    @ApiResponse(responseCode = "401", description = "UNAUTHORIZED",
            content = @Content(schema = @Schema(implementation = ErrorResponse.class)))
    @PostMapping("/logout")
    public ResponseEntity<Void> logout(@AuthenticationPrincipal AuthenticatedUser user) {
        authService.logout(user.userId());
        return ResponseEntity.noContent().build();
    }

    @Operation(summary = "Request a password reset code (screens 01-05, 01-06 resend)",
            description = "Emails a 6-digit reset code. Answers 202 the same way for unknown emails.")
    @ApiResponse(responseCode = "202", description = "Code sent; go to 01-06")
    @PostMapping("/password/forgot")
    public ResponseEntity<CodeDispatchResponse> forgotPassword(@Valid @RequestBody EmailRequest request) {
        return ResponseEntity.accepted().body(authService.forgotPassword(request));
    }

    @Operation(summary = "Verify the reset code (screen 01-06)",
            description = "Returns a short-lived resetToken for the set-new-password step.")
    @ApiResponse(responseCode = "200", description = "Code accepted; go to 01-07")
    @PostMapping("/password/verify-code")
    public ResetCodeVerifiedResponse verifyResetCode(@Valid @RequestBody VerifyCodeRequest request) {
        return authService.verifyResetCode(request);
    }

    @Operation(summary = "Set a new password (screens 01-07, 01-08)",
            description = "WEAK_PASSWORD (one fieldError per rule), PASSWORDS_DO_NOT_MATCH, PASSWORD_REUSED or "
                    + "INVALID_RESET_TOKEN. On success the user is signed out on every device.")
    @ApiResponse(responseCode = "200", description = "Password updated; go to 01-08")
    @PostMapping("/password/reset")
    public MessageResponse resetPassword(@Valid @RequestBody ResetPasswordRequest request) {
        return authService.resetPassword(request);
    }
}
