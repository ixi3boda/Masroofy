package com.masroofy.backend.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.masroofy.backend.model.AuthCode;
import com.masroofy.backend.model.AuthCodePurpose;
import com.masroofy.backend.model.User;
import java.time.Instant;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import com.masroofy.backend.support.PostgresTestSupport;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.context.annotation.Import;

@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import({UserRepository.class, AuthCodeRepository.class})
class AuthCodeRepositoryTest extends PostgresTestSupport {

    private static final Instant NOW = Instant.parse("2026-11-19T10:00:00Z");

    @Autowired
    private UserRepository userRepository;
    @Autowired
    private AuthCodeRepository repository;

    private UUID userId;

    @BeforeEach
    void setUp() {
        User user = UserRepositoryTest.newUser("mariam@example.com", "uid-1");
        userRepository.insert(user);
        userId = user.id();
    }

    private AuthCode code(AuthCodePurpose purpose, String hash, Instant createdAt, Instant expiresAt) {
        AuthCode code = new AuthCode(UUID.randomUUID(), userId, purpose, hash, 0, expiresAt, null, createdAt);
        repository.insert(code);
        return code;
    }

    @Test
    void findLatestReturnsNewestRegardlessOfState() {
        code(AuthCodePurpose.EMAIL_VERIFICATION, "h1", NOW.minusSeconds(120), NOW.plusSeconds(480));
        AuthCode newest = code(AuthCodePurpose.EMAIL_VERIFICATION, "h2", NOW.minusSeconds(10), NOW.plusSeconds(590));
        repository.consume(newest.id(), NOW);

        assertThat(repository.findLatest(userId, AuthCodePurpose.EMAIL_VERIFICATION))
                .get().extracting(AuthCode::id).isEqualTo(newest.id());
        assertThat(repository.findLatest(userId, AuthCodePurpose.PASSWORD_RESET)).isEmpty();
    }

    @Test
    void findLatestActiveSkipsExpiredAndConsumedCodes() {
        AuthCode valid = code(AuthCodePurpose.PASSWORD_RESET, "h1", NOW.minusSeconds(300), NOW.plusSeconds(300));
        code(AuthCodePurpose.PASSWORD_RESET, "h2", NOW.minusSeconds(900), NOW.minusSeconds(1));

        assertThat(repository.findLatestActive(userId, AuthCodePurpose.PASSWORD_RESET, NOW))
                .get().satisfies(found -> {
                    assertThat(found.id()).isEqualTo(valid.id());
                    assertThat(found.purpose()).isEqualTo(AuthCodePurpose.PASSWORD_RESET);
                    assertThat(found.codeHash()).isEqualTo("h1");
                    assertThat(found.expiresAt()).isEqualTo(NOW.plusSeconds(300));
                    assertThat(found.isActive(NOW)).isTrue();
                });

        repository.consume(valid.id(), NOW);
        assertThat(repository.findLatestActive(userId, AuthCodePurpose.PASSWORD_RESET, NOW)).isEmpty();
    }

    @Test
    void consumeSucceedsOnlyOnce() {
        AuthCode code = code(AuthCodePurpose.EMAIL_VERIFICATION, "h1", NOW, NOW.plusSeconds(600));

        assertThat(repository.consume(code.id(), NOW)).isTrue();
        assertThat(repository.consume(code.id(), NOW)).isFalse();
    }

    @Test
    void incrementAttemptsReturnsNewCountAndZeroOnceConsumed() {
        AuthCode code = code(AuthCodePurpose.EMAIL_VERIFICATION, "h1", NOW, NOW.plusSeconds(600));

        assertThat(repository.incrementAttempts(code.id())).isEqualTo(1);
        assertThat(repository.incrementAttempts(code.id())).isEqualTo(2);
        repository.consume(code.id(), NOW);
        assertThat(repository.incrementAttempts(code.id())).isZero();
    }

    @Test
    void invalidateActiveClosesOnlyThatPurpose() {
        code(AuthCodePurpose.EMAIL_VERIFICATION, "h1", NOW, NOW.plusSeconds(600));
        code(AuthCodePurpose.EMAIL_VERIFICATION, "h2", NOW.plusSeconds(1), NOW.plusSeconds(601));
        AuthCode reset = code(AuthCodePurpose.PASSWORD_RESET, "h3", NOW, NOW.plusSeconds(600));

        assertThat(repository.invalidateActive(userId, AuthCodePurpose.EMAIL_VERIFICATION, NOW)).isEqualTo(2);
        assertThat(repository.findLatestActive(userId, AuthCodePurpose.EMAIL_VERIFICATION, NOW)).isEmpty();
        assertThat(repository.findLatestActive(userId, AuthCodePurpose.PASSWORD_RESET, NOW))
                .get().extracting(AuthCode::id).isEqualTo(reset.id());
    }

    @Test
    void findActiveByHashMatchesPurposeAndExpiry() {
        AuthCode token = code(AuthCodePurpose.PASSWORD_RESET_TOKEN, "tokhash", NOW, NOW.plusSeconds(900));

        assertThat(repository.findActiveByHash(AuthCodePurpose.PASSWORD_RESET_TOKEN, "tokhash", NOW))
                .get().extracting(AuthCode::id).isEqualTo(token.id());
        assertThat(repository.findActiveByHash(AuthCodePurpose.PASSWORD_RESET, "tokhash", NOW)).isEmpty();
        assertThat(repository.findActiveByHash(AuthCodePurpose.PASSWORD_RESET_TOKEN, "tokhash",
                NOW.plusSeconds(900))).isEmpty();
    }
}
