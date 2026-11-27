package com.masroofy.backend.controller;

import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

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
import com.masroofy.backend.dto.response.UserResponse;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.AuthService;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.WebMvcTest;
import org.springframework.context.annotation.Import;
import org.springframework.http.MediaType;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

import com.fasterxml.jackson.databind.ObjectMapper;

@WebMvcTest(AuthController.class)
@Import(WebLayerTestConfig.class)
class AuthControllerTest {

    private static final Instant NOW = Instant.parse("2026-11-19T10:00:00Z");
    private static final UserResponse USER = new UserResponse(
            UUID.fromString("22222222-2222-2222-2222-222222222222"), "Mariam Ali", "mariam@example.com", null,
            "EGP", "en", "Africa/Cairo", true, NOW, NOW);

    @Autowired
    private MockMvc mvc;
    @Autowired
    private ObjectMapper json;

    @MockitoBean
    private AuthService authService;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private UserRepository userRepository;

    private String body(Object value) throws Exception {
        return json.writeValueAsString(value);
    }

    @Test
    void registerReturns201WithUserAndVerificationInfo() throws Exception {
        UserResponse unverified = new UserResponse(USER.id(), USER.fullName(), USER.email(), null, "EGP", "en",
                "Africa/Cairo", false, null, NOW);
        when(authService.register(any())).thenReturn(new RegisterResponse(unverified,
                new CodeDispatchResponse("m***@example.com", 6, 600, 60), true));

        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new RegisterRequest("Mariam Ali", "mariam@example.com", "Sunny-Nile9", true))))
                .andExpect(status().isCreated())
                .andExpect(jsonPath("$.user.id").value(USER.id().toString()))
                .andExpect(jsonPath("$.user.fullName").value("Mariam Ali"))
                .andExpect(jsonPath("$.user.emailVerified").value(false))
                .andExpect(jsonPath("$.user.baseCurrency").value("EGP"))
                .andExpect(jsonPath("$.user.createdAt").value("2026-11-19T10:00:00Z"))
                .andExpect(jsonPath("$.user.emailVerifiedAt").doesNotExist())
                .andExpect(jsonPath("$.user.firebaseUid").doesNotExist())
                .andExpect(jsonPath("$.verification.maskedEmail").value("m***@example.com"))
                .andExpect(jsonPath("$.verification.codeLength").value(6))
                .andExpect(jsonPath("$.verification.resendAvailableInSeconds").value(60))
                .andExpect(jsonPath("$.verificationEmailSent").value(true));
    }

    @Test
    void databaseDownIs503ServiceUnavailable() throws Exception {
        when(authService.register(any()))
                .thenThrow(new org.springframework.transaction.CannotCreateTransactionException("db down"));

        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new RegisterRequest("Mariam Ali", "mariam@example.com", "Sunny-Nile9", true))))
                .andExpect(status().isServiceUnavailable())
                .andExpect(jsonPath("$.code").value("SERVICE_UNAVAILABLE"));
    }

    @Test
    void registerValidatesEveryField() throws Exception {
        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"fullName\":\" \",\"email\":\"not-an-email\",\"password\":\"\",\"acceptedTerms\":false}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("VALIDATION_FAILED"))
                .andExpect(jsonPath("$.status").value(400))
                .andExpect(jsonPath("$.path").value("/api/v1/auth/register"))
                .andExpect(jsonPath("$.fieldErrors[?(@.field=='fullName')]").exists())
                .andExpect(jsonPath("$.fieldErrors[?(@.field=='email')]").exists())
                .andExpect(jsonPath("$.fieldErrors[?(@.field=='password')]").exists())
                .andExpect(jsonPath("$.fieldErrors[?(@.field=='acceptedTerms')].message")
                        .value("You must agree to the Terms & Privacy Policy"));
        verifyNoInteractions(authService);
    }

    @Test
    void registerRequiresTermsField() throws Exception {
        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"fullName\":\"Mariam\",\"email\":\"m@example.com\",\"password\":\"Sunny-Nile9\"}"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("acceptedTerms"));
    }

    @Test
    void emailWithoutDomainEndingIsRejected() throws Exception {
        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new RegisterRequest("Mariam Ali", "mariam@localhost", "Sunny-Nile9", true))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("email"));
        verifyNoInteractions(authService);
    }

    @Test
    void spacesAroundEmailNameAndCodeAreIgnored() throws Exception {
        when(authService.register(any())).thenReturn(new RegisterResponse(USER,
                new CodeDispatchResponse("m***@example.com", 6, 600, 60), true));
        when(authService.verifyEmail(any())).thenReturn(new EmailVerifiedResponse("mariam@example.com", true));

        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"fullName\":\" Mariam Ali \",\"email\":\" mariam@example.com \","
                                + "\"password\":\"Sunny-Nile9\",\"acceptedTerms\":true}"))
                .andExpect(status().isCreated());
        mvc.perform(post("/api/v1/auth/email-verification/verify").contentType(MediaType.APPLICATION_JSON)
                        .content("{\"email\":\"mariam@example.com \",\"code\":\" 042517 \"}"))
                .andExpect(status().isOk());

        org.mockito.ArgumentCaptor<RegisterRequest> registered = org.mockito.ArgumentCaptor.forClass(RegisterRequest.class);
        verify(authService).register(registered.capture());
        org.assertj.core.api.Assertions.assertThat(registered.getValue().email()).isEqualTo("mariam@example.com");
        org.assertj.core.api.Assertions.assertThat(registered.getValue().fullName()).isEqualTo("Mariam Ali");
        org.assertj.core.api.Assertions.assertThat(registered.getValue().password()).isEqualTo("Sunny-Nile9");
        org.mockito.ArgumentCaptor<VerifyCodeRequest> verified = org.mockito.ArgumentCaptor.forClass(VerifyCodeRequest.class);
        verify(authService).verifyEmail(verified.capture());
        org.assertj.core.api.Assertions.assertThat(verified.getValue().code()).isEqualTo("042517");
    }

    @Test
    void wrongHttpMethodIs405() throws Exception {
        mvc.perform(org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get("/api/v1/auth/login"))
                .andExpect(status().isMethodNotAllowed())
                .andExpect(jsonPath("$.code").value("METHOD_NOT_ALLOWED"));
    }

    @Test
    void malformedJsonIsA400() throws Exception {
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON).content("{oops"))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("MALFORMED_REQUEST"));
    }

    @Test
    void duplicateEmailIsA409() throws Exception {
        when(authService.register(any())).thenThrow(new ApiException(ErrorCode.EMAIL_ALREADY_IN_USE));

        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new RegisterRequest("Mariam Ali", "mariam@example.com", "Sunny-Nile9", true))))
                .andExpect(status().isConflict())
                .andExpect(jsonPath("$.code").value("EMAIL_ALREADY_IN_USE"))
                .andExpect(jsonPath("$.message").value("An account with this email already exists."));
    }

    @Test
    void weakPasswordReturnsRuleByRuleFieldErrors() throws Exception {
        when(authService.register(any())).thenThrow(new ApiException(ErrorCode.WEAK_PASSWORD, "x", Map.of(),
                java.util.List.of(new com.masroofy.backend.exception.FieldErrorDetail("password", "MIN_LENGTH",
                        "Use at least 8 characters")), null));

        mvc.perform(post("/api/v1/auth/register").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new RegisterRequest("Mariam Ali", "mariam@example.com", "short", true))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("WEAK_PASSWORD"))
                .andExpect(jsonPath("$.fieldErrors[0].code").value("MIN_LENGTH"));
    }

    @Test
    void verifyEmailReturns200() throws Exception {
        when(authService.verifyEmail(any())).thenReturn(new EmailVerifiedResponse("mariam@example.com", true));

        mvc.perform(post("/api/v1/auth/email-verification/verify").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new VerifyCodeRequest("mariam@example.com", "042517"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.emailVerified").value(true));
    }

    @Test
    void verifyEmailRejectsNonNumericCode() throws Exception {
        mvc.perform(post("/api/v1/auth/email-verification/verify").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new VerifyCodeRequest("mariam@example.com", "12ab56"))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.fieldErrors[0].field").value("code"));
    }

    @Test
    void wrongCodeReportsRemainingAttempts() throws Exception {
        when(authService.verifyEmail(any()))
                .thenThrow(new ApiException(ErrorCode.INVALID_CODE, Map.of("remainingAttempts", 3)));

        mvc.perform(post("/api/v1/auth/email-verification/verify").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new VerifyCodeRequest("mariam@example.com", "000000"))))
                .andExpect(status().isBadRequest())
                .andExpect(jsonPath("$.code").value("INVALID_CODE"))
                .andExpect(jsonPath("$.details.remainingAttempts").value(3));
    }

    @Test
    void resendReturns202AndCooldownReturns429WithRetryAfter() throws Exception {
        when(authService.resendVerificationCode(any()))
                .thenReturn(new CodeDispatchResponse("m***@example.com", 6, 600, 60))
                .thenThrow(new ApiException(ErrorCode.RESEND_COOLDOWN, Map.of("retryAfterSeconds", 42L)));

        mvc.perform(post("/api/v1/auth/email-verification/resend").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new EmailRequest("mariam@example.com"))))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.maskedEmail").value("m***@example.com"));

        mvc.perform(post("/api/v1/auth/email-verification/resend").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new EmailRequest("mariam@example.com"))))
                .andExpect(status().isTooManyRequests())
                .andExpect(header().string("Retry-After", "42"))
                .andExpect(jsonPath("$.details.retryAfterSeconds").value(42));
    }

    @Test
    void loginReturnsTokensAndUser() throws Exception {
        when(authService.login(any())).thenReturn(new AuthTokensResponse("id-token", "refresh", "Bearer", 3600, USER));

        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new LoginRequest("mariam@example.com", "Sunny-Nile9"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").value("id-token"))
                .andExpect(jsonPath("$.refreshToken").value("refresh"))
                .andExpect(jsonPath("$.tokenType").value("Bearer"))
                .andExpect(jsonPath("$.expiresIn").value(3600))
                .andExpect(jsonPath("$.user.email").value("mariam@example.com"));
    }

    @Test
    void loginWithStaleBearerTokenStillWorks() throws Exception {
        when(authService.login(any())).thenReturn(new AuthTokensResponse("id-token", "refresh", "Bearer", 3600, USER));

        mvc.perform(post("/api/v1/auth/login").header("Authorization", "Bearer expired")
                        .contentType(MediaType.APPLICATION_JSON)
                        .content(body(new LoginRequest("mariam@example.com", "Sunny-Nile9"))))
                .andExpect(status().isOk());
        verifyNoInteractions(firebase);
    }

    @Test
    void loginErrorsMapToStatusCodes() throws Exception {
        when(authService.login(any()))
                .thenThrow(new ApiException(ErrorCode.INVALID_CREDENTIALS))
                .thenThrow(new ApiException(ErrorCode.EMAIL_NOT_VERIFIED, Map.of("maskedEmail", "m***@example.com")));
        String request = body(new LoginRequest("mariam@example.com", "wrong-pass1"));

        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON).content(request))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("INVALID_CREDENTIALS"));
        mvc.perform(post("/api/v1/auth/login").contentType(MediaType.APPLICATION_JSON).content(request))
                .andExpect(status().isForbidden())
                .andExpect(jsonPath("$.code").value("EMAIL_NOT_VERIFIED"))
                .andExpect(jsonPath("$.details.maskedEmail").value("m***@example.com"));
    }

    @Test
    void refreshReturnsTokens() throws Exception {
        when(authService.refresh(any())).thenReturn(new AuthTokensResponse("new-id", "new-refresh", "Bearer", 3600, USER));

        mvc.perform(post("/api/v1/auth/token/refresh").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new RefreshTokenRequest("refresh"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.accessToken").value("new-id"));
    }

    @Test
    void forgotPasswordReturns202() throws Exception {
        when(authService.forgotPassword(any())).thenReturn(new CodeDispatchResponse("m***@example.com", 6, 600, 60));

        mvc.perform(post("/api/v1/auth/password/forgot").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new EmailRequest("mariam@example.com"))))
                .andExpect(status().isAccepted())
                .andExpect(jsonPath("$.codeLength").value(6));
    }

    @Test
    void verifyResetCodeReturnsResetToken() throws Exception {
        when(authService.verifyResetCode(any())).thenReturn(new ResetCodeVerifiedResponse("reset-token", 900));

        mvc.perform(post("/api/v1/auth/password/verify-code").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new VerifyCodeRequest("mariam@example.com", "123456"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.resetToken").value("reset-token"))
                .andExpect(jsonPath("$.expiresInSeconds").value(900));
    }

    @Test
    void resetPasswordReturns200() throws Exception {
        when(authService.resetPassword(any())).thenReturn(new MessageResponse("Your password has been reset successfully."));

        mvc.perform(post("/api/v1/auth/password/reset").contentType(MediaType.APPLICATION_JSON)
                        .content(body(new ResetPasswordRequest("reset-token", "Fresh-Start7", "Fresh-Start7"))))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.message").value("Your password has been reset successfully."));
    }

    @Test
    void logoutRequiresAToken() throws Exception {
        mvc.perform(post("/api/v1/auth/logout"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
        verifyNoInteractions(authService);
    }

    @Test
    void logoutWithValidTokenRevokesSessions() throws Exception {
        User user = new User(USER.id(), "uid-1", USER.email(), null, USER.fullName(), "EGP", "en", "Africa/Cairo",
                null, NOW, NOW, NOW, NOW);
        when(firebase.verifyIdToken("good", true)).thenReturn(new VerifiedToken("uid-1", USER.email()));
        when(userRepository.findByFirebaseUid("uid-1")).thenReturn(Optional.of(user));

        mvc.perform(post("/api/v1/auth/logout").header("Authorization", "Bearer good"))
                .andExpect(status().isNoContent());
        verify(authService).logout(USER.id());
    }
}
