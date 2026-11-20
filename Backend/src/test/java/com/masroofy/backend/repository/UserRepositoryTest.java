package com.masroofy.backend.repository;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.masroofy.backend.model.User;
import java.time.Instant;
import java.time.temporal.ChronoUnit;
import java.util.UUID;
import com.masroofy.backend.support.PostgresTestSupport;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.context.annotation.Import;
import org.springframework.dao.DuplicateKeyException;

@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import(UserRepository.class)
class UserRepositoryTest extends PostgresTestSupport {

    private static final Instant NOW = Instant.parse("2026-11-19T10:00:00Z");

    @Autowired
    private UserRepository repository;

    static User newUser(String email, String uid) {
        return new User(UUID.randomUUID(), uid, email, null, "Mariam Ali", "EGP", "en", "Africa/Cairo", null,
                null, NOW, NOW, NOW);
    }

    @Test
    void insertAndFindByEveryKey() {
        User user = newUser("mariam@example.com", "uid-1");
        repository.insert(user);

        assertThat(repository.findById(user.id())).contains(user);
        assertThat(repository.findByEmail("mariam@example.com")).contains(user);
        assertThat(repository.findByFirebaseUid("uid-1")).contains(user);
        assertThat(repository.existsByEmail("mariam@example.com")).isTrue();
    }

    @Test
    void missingUsersAreEmpty() {
        assertThat(repository.findById(UUID.randomUUID())).isEmpty();
        assertThat(repository.findByEmail("ghost@example.com")).isEmpty();
        assertThat(repository.findByFirebaseUid("ghost")).isEmpty();
        assertThat(repository.existsByEmail("ghost@example.com")).isFalse();
    }

    // PostgreSQL aborts the transaction after a constraint violation, so each case gets its own test.
    @Test
    void emailIsUnique() {
        repository.insert(newUser("mariam@example.com", "uid-1"));

        assertThatThrownBy(() -> repository.insert(newUser("mariam@example.com", "uid-2")))
                .isInstanceOf(DuplicateKeyException.class);
    }

    @Test
    void firebaseUidIsUnique() {
        repository.insert(newUser("mariam@example.com", "uid-1"));

        assertThatThrownBy(() -> repository.insert(newUser("other@example.com", "uid-1")))
                .isInstanceOf(DuplicateKeyException.class);
    }

    @Test
    void manyUsersMayHaveNoPhone() {
        repository.insert(newUser("a@example.com", "uid-a"));
        repository.insert(newUser("b@example.com", "uid-b"));

        assertThat(repository.existsByEmail("b@example.com")).isTrue();
    }

    @Test
    void emailLockCanBeTakenInsideATransaction() {
        // @JdbcTest runs each test in a transaction, which is where the advisory lock lives.
        repository.lockEmail("mariam@example.com");
        repository.lockEmail("mariam@example.com");   // re-entrant for the same transaction
        assertThat(repository.existsByEmail("mariam@example.com")).isFalse();
    }

    @Test
    void markEmailVerifiedOnlyOnce() {
        User user = newUser("mariam@example.com", "uid-1");
        repository.insert(user);
        Instant verifiedAt = NOW.plus(5, ChronoUnit.MINUTES);

        assertThat(repository.markEmailVerified(user.id(), verifiedAt)).isEqualTo(1);
        assertThat(repository.markEmailVerified(user.id(), verifiedAt.plusSeconds(60))).isZero();

        User reloaded = repository.findById(user.id()).orElseThrow();
        assertThat(reloaded.emailVerifiedAt()).isEqualTo(verifiedAt);
        assertThat(reloaded.updatedAt()).isEqualTo(verifiedAt);
        assertThat(reloaded.isEmailVerified()).isTrue();
    }

    @Test
    void sessionVersionStartsAtZeroAndOnlyGoesUp() {
        User user = newUser("mariam@example.com", "uid-1");
        repository.insert(user);
        assertThat(repository.findById(user.id()).orElseThrow().sessionVersion()).isZero();

        assertThat(repository.raiseSessionVersion(user.id(), 2)).isEqualTo(1);
        assertThat(repository.findById(user.id()).orElseThrow().sessionVersion()).isEqualTo(2);

        // A late, stale logout must not lower it.
        repository.raiseSessionVersion(user.id(), 1);
        assertThat(repository.findById(user.id()).orElseThrow().sessionVersion()).isEqualTo(2);
    }
}
