package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.masroofy.backend.config.AuthProperties;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.model.AuthCode;
import com.masroofy.backend.model.AuthCodePurpose;
import com.masroofy.backend.repository.AuthCodeRepository;
import com.masroofy.backend.service.AuthCodeService.IssuedCode;
import com.masroofy.backend.service.AuthCodeService.IssuedToken;
import com.masroofy.backend.util.SecureCodes;
import java.security.SecureRandom;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class AuthCodeServiceTest {

    private static final Instant NOW = Instant.parse("2026-11-19T10:00:00Z");
    private static final UUID USER_ID = UUID.fromString("11111111-1111-1111-1111-111111111111");

    @Mock
    private AuthCodeRepository repository;

    private final SecureCodes secureCodes =
            new SecureCodes("test-secret-test-secret-test-secret-123", new SecureRandom());
    private final AuthProperties properties = new AuthProperties("test-secret-test-secret-test-secret-123", 6,
            Duration.ofMinutes(10), 5, Duration.ofSeconds(60), Duration.ofMinutes(15));

    private AuthCodeService service;

    @BeforeEach
    void setUp() {
        service = new AuthCodeService(repository, secureCodes, properties, Clock.fixed(NOW, ZoneOffset.UTC));
    }

    private AuthCode code(String plain, int attempts, Instant createdAt) {
        return new AuthCode(UUID.randomUUID(), USER_ID, AuthCodePurpose.EMAIL_VERIFICATION,
                secureCodes.hash(plain), attempts, createdAt.plus(Duration.ofMinutes(10)), null, createdAt);
    }

    // ---- issueCode ----

    @Test
    void issueCodeStoresOnlyTheHashAndInvalidatesOlderCodes() {
        when(repository.findLatest(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION)).thenReturn(Optional.empty());

        IssuedCode issued = service.issueCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION);

        assertThat(issued.code()).hasSize(6).containsOnlyDigits();
        assertThat(issued.expiresAt()).isEqualTo(NOW.plus(Duration.ofMinutes(10)));
        verify(repository).invalidateActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW);
        ArgumentCaptor<AuthCode> saved = ArgumentCaptor.forClass(AuthCode.class);
        verify(repository).insert(saved.capture());
        assertThat(saved.getValue().codeHash()).isEqualTo(secureCodes.hash(issued.code()))
                .isNotEqualTo(issued.code());
        assertThat(saved.getValue().attempts()).isZero();
        assertThat(saved.getValue().createdAt()).isEqualTo(NOW);
    }

    @Test
    void issueCodeEnforcesResendCooldown() {
        when(repository.findLatest(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION))
                .thenReturn(Optional.of(code("123456", 0, NOW.minusSeconds(20))));

        assertThatThrownBy(() -> service.issueCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.getErrorCode()).isEqualTo(ErrorCode.RESEND_COOLDOWN);
                    assertThat(e.getDetails()).containsEntry("retryAfterSeconds", 40L);
                });
        verify(repository, never()).insert(any());
    }

    @Test
    void issueCodeAllowedOnceCooldownHasPassed() {
        when(repository.findLatest(USER_ID, AuthCodePurpose.PASSWORD_RESET))
                .thenReturn(Optional.of(code("123456", 0, NOW.minusSeconds(60))));

        assertThat(service.issueCode(USER_ID, AuthCodePurpose.PASSWORD_RESET).code()).hasSize(6);
    }

    @Test
    void issueCodeRejectsResetTokenPurpose() {
        assertThatThrownBy(() -> service.issueCode(USER_ID, AuthCodePurpose.PASSWORD_RESET_TOKEN))
                .isInstanceOf(IllegalArgumentException.class);
    }

    // ---- verifyCode ----

    @Test
    void verifyCodeConsumesMatchingCode() {
        AuthCode active = code("042517", 0, NOW.minusSeconds(30));
        when(repository.findLatestActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW))
                .thenReturn(Optional.of(active));
        when(repository.consume(active.id(), NOW)).thenReturn(true);

        service.verifyCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, "042517");

        verify(repository).consume(active.id(), NOW);
        verify(repository, never()).incrementAttempts(any());
    }

    @Test
    void verifyCodeFailsWhenNoActiveCode() {
        when(repository.findLatestActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW))
                .thenReturn(Optional.empty());

        assertError(() -> service.verifyCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, "042517"),
                ErrorCode.INVALID_OR_EXPIRED_CODE);
    }

    @Test
    void wrongCodeCountsAnAttemptAndReportsRemaining() {
        AuthCode active = code("042517", 1, NOW.minusSeconds(30));
        when(repository.findLatestActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW))
                .thenReturn(Optional.of(active));
        when(repository.incrementAttempts(active.id())).thenReturn(2);

        assertThatThrownBy(() -> service.verifyCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, "111111"))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.getErrorCode()).isEqualTo(ErrorCode.INVALID_CODE);
                    assertThat(e.getDetails()).containsEntry("remainingAttempts", 3);
                });
        verify(repository, never()).consume(any(), any());
    }

    @Test
    void lastWrongAttemptBurnsTheCode() {
        AuthCode active = code("042517", 4, NOW.minusSeconds(30));
        when(repository.findLatestActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW))
                .thenReturn(Optional.of(active));
        when(repository.incrementAttempts(active.id())).thenReturn(5);

        assertError(() -> service.verifyCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, "111111"),
                ErrorCode.TOO_MANY_ATTEMPTS);
        verify(repository).consume(active.id(), NOW);
    }

    @Test
    void codeAlreadyAtMaxAttemptsIsRejectedEvenIfCorrect() {
        AuthCode active = code("042517", 5, NOW.minusSeconds(30));
        when(repository.findLatestActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW))
                .thenReturn(Optional.of(active));

        assertError(() -> service.verifyCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, "042517"),
                ErrorCode.TOO_MANY_ATTEMPTS);
    }

    @Test
    void wrongCodeOnConcurrentlyConsumedCodeIsInvalid() {
        AuthCode active = code("042517", 0, NOW.minusSeconds(30));
        when(repository.findLatestActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW))
                .thenReturn(Optional.of(active));
        when(repository.incrementAttempts(active.id())).thenReturn(0);

        assertError(() -> service.verifyCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, "111111"),
                ErrorCode.INVALID_OR_EXPIRED_CODE);
    }

    @Test
    void correctCodeLosingTheConsumeRaceIsInvalid() {
        AuthCode active = code("042517", 0, NOW.minusSeconds(30));
        when(repository.findLatestActive(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, NOW))
                .thenReturn(Optional.of(active));
        when(repository.consume(active.id(), NOW)).thenReturn(false);

        assertError(() -> service.verifyCode(USER_ID, AuthCodePurpose.EMAIL_VERIFICATION, "042517"),
                ErrorCode.INVALID_OR_EXPIRED_CODE);
    }

    // ---- reset tokens ----

    @Test
    void issueResetTokenStoresHashAndReplacesOlderTokens() {
        IssuedToken token = service.issueResetToken(USER_ID);

        assertThat(token.expiresAt()).isEqualTo(NOW.plus(Duration.ofMinutes(15)));
        verify(repository).invalidateActive(USER_ID, AuthCodePurpose.PASSWORD_RESET_TOKEN, NOW);
        ArgumentCaptor<AuthCode> saved = ArgumentCaptor.forClass(AuthCode.class);
        verify(repository).insert(saved.capture());
        assertThat(saved.getValue().purpose()).isEqualTo(AuthCodePurpose.PASSWORD_RESET_TOKEN);
        assertThat(saved.getValue().codeHash()).isEqualTo(secureCodes.hash(token.token()));
    }

    @Test
    void findActiveResetTokenLooksUpByHash() {
        AuthCode stored = new AuthCode(UUID.randomUUID(), USER_ID, AuthCodePurpose.PASSWORD_RESET_TOKEN,
                secureCodes.hash("tok"), 0, NOW.plusSeconds(60), null, NOW);
        when(repository.findActiveByHash(AuthCodePurpose.PASSWORD_RESET_TOKEN, secureCodes.hash("tok"), NOW))
                .thenReturn(Optional.of(stored));

        assertThat(service.findActiveResetToken("tok")).isEqualTo(stored);
    }

    @Test
    void unknownResetTokenIsRejected() {
        when(repository.findActiveByHash(eq(AuthCodePurpose.PASSWORD_RESET_TOKEN), anyString(), eq(NOW)))
                .thenReturn(Optional.empty());

        assertError(() -> service.findActiveResetToken("nope"), ErrorCode.INVALID_RESET_TOKEN);
    }

    @Test
    void secondsUntilRoundsUpAndNeverGoesNegative() {
        assertThat(service.secondsUntil(NOW.plusMillis(1500))).isEqualTo(2);
        assertThat(service.secondsUntil(NOW.minusSeconds(5))).isZero();
    }

    private static void assertError(Runnable call, ErrorCode expected) {
        assertThatThrownBy(call::run)
                .isInstanceOfSatisfying(ApiException.class, e -> assertThat(e.getErrorCode()).isEqualTo(expected));
    }
}
