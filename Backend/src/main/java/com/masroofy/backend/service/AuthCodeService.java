package com.masroofy.backend.service;

import com.masroofy.backend.config.AuthProperties;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.model.AuthCode;
import com.masroofy.backend.model.AuthCodePurpose;
import com.masroofy.backend.repository.AuthCodeRepository;
import com.masroofy.backend.repository.CodeDispatchRepository;
import com.masroofy.backend.util.SecureCodes;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/** Issues and checks one-time email codes and password-reset tokens. */
@Service
public class AuthCodeService {

    /** Rows older than this can no longer block a resend, so they are purged. */
    private static final Duration DISPATCH_RETENTION = Duration.ofDays(1);

    private final AuthCodeRepository repository;
    private final CodeDispatchRepository dispatchRepository;
    private final SecureCodes secureCodes;
    private final AuthProperties properties;
    private final Clock clock;
    private final TransactionTemplate transactionTemplate;

    public AuthCodeService(AuthCodeRepository repository, CodeDispatchRepository dispatchRepository,
                           SecureCodes secureCodes, AuthProperties properties, Clock clock,
                           TransactionTemplate transactionTemplate) {
        this.repository = repository;
        this.dispatchRepository = dispatchRepository;
        this.secureCodes = secureCodes;
        this.properties = properties;
        this.clock = clock;
        this.transactionTemplate = transactionTemplate;
    }

    private enum Verdict { ACCEPTED, NO_ACTIVE_CODE, TOO_MANY_ATTEMPTS, WRONG_CODE }

    private record Outcome(Verdict verdict, int remainingAttempts) {
        static Outcome of(Verdict verdict) {
            return new Outcome(verdict, 0);
        }
    }

    public record IssuedCode(String code, Instant expiresAt) {
        @Override
        public String toString() {
            return "IssuedCode[code=***, expiresAt=" + expiresAt + "]";
        }
    }

    public record IssuedToken(String token, Instant expiresAt) {
        @Override
        public String toString() {
            return "IssuedToken[token=***, expiresAt=" + expiresAt + "]";
        }
    }

    /**
     * Creates a new code and invalidates older ones of the same purpose.
     *
     * @throws ApiException {@link ErrorCode#RESEND_COOLDOWN} when the previous code was issued too recently
     */
    public IssuedCode issueCode(UUID userId, AuthCodePurpose purpose) {
        requireCodePurpose(purpose);
        return transactionTemplate.execute(status -> issueCodeLocked(userId, purpose));
    }

    private IssuedCode issueCodeLocked(UUID userId, AuthCodePurpose purpose) {
        repository.lockUser(userId);
        Instant now = clock.instant();
        Optional<AuthCode> latest = repository.findLatest(userId, purpose);
        if (latest.isPresent()) {
            Instant availableAt = latest.get().createdAt().plus(properties.resendCooldown());
            if (availableAt.isAfter(now)) {
                long retryAfter = ceilSeconds(Duration.between(now, availableAt));
                throw new ApiException(ErrorCode.RESEND_COOLDOWN, Map.of("retryAfterSeconds", retryAfter));
            }
        }
        repository.invalidateActive(userId, purpose, now);
        String code = secureCodes.numericCode(properties.codeLength());
        Instant expiresAt = now.plus(properties.codeTtl());
        repository.insert(new AuthCode(UUID.randomUUID(), userId, purpose, secureCodes.hash(code), 0, expiresAt,
                null, now));
        return new IssuedCode(code, expiresAt);
    }

    /**
     * Checks the code against the newest active one and consumes it on success.
     * Wrong codes count toward {@code max-code-attempts}; after that the code is burned.
     */
    public void verifyCode(UUID userId, AuthCodePurpose purpose, String code) {
        requireCodePurpose(purpose);
        // Decide inside the locked transaction, throw after it commits: a failed attempt must stay counted.
        Outcome outcome = transactionTemplate.execute(status -> verifyCodeLocked(userId, purpose, code));
        switch (outcome.verdict()) {
            case ACCEPTED -> { }
            case NO_ACTIVE_CODE -> throw new ApiException(ErrorCode.INVALID_OR_EXPIRED_CODE);
            case TOO_MANY_ATTEMPTS -> throw new ApiException(ErrorCode.TOO_MANY_ATTEMPTS);
            case WRONG_CODE -> throw new ApiException(ErrorCode.INVALID_CODE,
                    Map.of("remainingAttempts", outcome.remainingAttempts()));
        }
    }

    private Outcome verifyCodeLocked(UUID userId, AuthCodePurpose purpose, String code) {
        repository.lockUser(userId);
        Instant now = clock.instant();
        Optional<AuthCode> found = repository.findLatestActive(userId, purpose, now);
        if (found.isEmpty()) {
            return Outcome.of(Verdict.NO_ACTIVE_CODE);
        }
        AuthCode active = found.get();
        if (active.attempts() >= properties.maxCodeAttempts()) {
            repository.consume(active.id(), now);
            return Outcome.of(Verdict.TOO_MANY_ATTEMPTS);
        }
        if (!secureCodes.matches(code, active.codeHash())) {
            int attempts = repository.incrementAttempts(active.id());
            if (attempts == 0) {
                return Outcome.of(Verdict.NO_ACTIVE_CODE);
            }
            int remaining = properties.maxCodeAttempts() - attempts;
            if (remaining <= 0) {
                repository.consume(active.id(), now);
                return Outcome.of(Verdict.TOO_MANY_ATTEMPTS);
            }
            return new Outcome(Verdict.WRONG_CODE, remaining);
        }
        if (!repository.consume(active.id(), now)) {
            return Outcome.of(Verdict.NO_ACTIVE_CODE);
        }
        return Outcome.of(Verdict.ACCEPTED);
    }

    /**
     * The resend cooldown for "Resend code" and "Forgot password", applied per email address BEFORE looking the
     * account up. Unknown and known emails therefore get identical answers, and parallel requests cannot share
     * one slot.
     *
     * @throws ApiException {@link ErrorCode#RESEND_COOLDOWN} with {@code retryAfterSeconds}
     */
    public void reserveDispatch(String normalizedEmail, AuthCodePurpose purpose) {
        requireCodePurpose(purpose);
        Instant now = clock.instant();
        dispatchRepository.deleteOlderThan(now.minus(DISPATCH_RETENTION));
        Optional<Instant> takenAt = dispatchRepository.reserve(dispatchKey(normalizedEmail, purpose), purpose, now,
                now.minus(properties.resendCooldown()));
        if (takenAt.isPresent()) {
            long retryAfter = Math.max(1, ceilSeconds(
                    Duration.between(now, takenAt.get().plus(properties.resendCooldown()))));
            throw new ApiException(ErrorCode.RESEND_COOLDOWN, Map.of("retryAfterSeconds", retryAfter));
        }
    }

    /** Starts the per-email cooldown without checking it (sign-up sends the first code). */
    public void recordDispatch(String normalizedEmail, AuthCodePurpose purpose) {
        requireCodePurpose(purpose);
        dispatchRepository.record(dispatchKey(normalizedEmail, purpose), purpose, clock.instant());
    }

    private String dispatchKey(String normalizedEmail, AuthCodePurpose purpose) {
        return secureCodes.hash("code-dispatch:" + purpose.name() + ":" + normalizedEmail);
    }

    /** Issues the token that authorises "Set new password"; any earlier reset token stops working. */
    public IssuedToken issueResetToken(UUID userId) {
        Instant now = clock.instant();
        repository.invalidateActive(userId, AuthCodePurpose.PASSWORD_RESET_TOKEN, now);
        String token = secureCodes.token();
        Instant expiresAt = now.plus(properties.resetTokenTtl());
        repository.insert(new AuthCode(UUID.randomUUID(), userId, AuthCodePurpose.PASSWORD_RESET_TOKEN,
                secureCodes.hash(token), 0, expiresAt, null, now));
        return new IssuedToken(token, expiresAt);
    }

    public AuthCode findActiveResetToken(String token) {
        return repository.findActiveByHash(AuthCodePurpose.PASSWORD_RESET_TOKEN, secureCodes.hash(token),
                        clock.instant())
                .orElseThrow(() -> new ApiException(ErrorCode.INVALID_RESET_TOKEN));
    }

    public boolean consume(AuthCode code) {
        return repository.consume(code.id(), clock.instant());
    }

    public long secondsUntil(Instant instant) {
        return Math.max(0, ceilSeconds(Duration.between(clock.instant(), instant)));
    }

    public int codeLength() {
        return properties.codeLength();
    }

    public long resendCooldownSeconds() {
        return properties.resendCooldown().toSeconds();
    }

    public long codeTtlSeconds() {
        return properties.codeTtl().toSeconds();
    }

    private static void requireCodePurpose(AuthCodePurpose purpose) {
        if (purpose == AuthCodePurpose.PASSWORD_RESET_TOKEN) {
            throw new IllegalArgumentException("Reset tokens are issued with issueResetToken");
        }
    }

    private static long ceilSeconds(Duration duration) {
        long seconds = duration.toSeconds();
        return duration.toNanosPart() > 0 ? seconds + 1 : seconds;
    }
}
