package com.masroofy.backend.repository;

import static org.assertj.core.api.Assertions.assertThat;

import com.masroofy.backend.model.AuthCodePurpose;
import com.masroofy.backend.support.PostgresTestSupport;
import java.time.Instant;
import org.junit.jupiter.api.Test;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.jdbc.AutoConfigureTestDatabase;
import org.springframework.boot.test.autoconfigure.jdbc.JdbcTest;
import org.springframework.context.annotation.Import;

@JdbcTest
@AutoConfigureTestDatabase(replace = AutoConfigureTestDatabase.Replace.NONE)
@Import(CodeDispatchRepository.class)
class CodeDispatchRepositoryTest extends PostgresTestSupport {

    private static final Instant NOW = Instant.parse("2026-11-20T10:00:00Z");
    private static final String KEY = "a".repeat(64);

    @Autowired
    private CodeDispatchRepository repository;

    @Test
    void firstReservationWinsAndTheNextOneSeesWhenTheSlotWasTaken() {
        assertThat(repository.reserve(KEY, AuthCodePurpose.PASSWORD_RESET, NOW, NOW.minusSeconds(60))).isEmpty();

        Instant later = NOW.plusSeconds(20);
        assertThat(repository.reserve(KEY, AuthCodePurpose.PASSWORD_RESET, later, later.minusSeconds(60)))
                .contains(NOW);
    }

    @Test
    void slotIsFreeAgainAfterTheCooldown() {
        repository.reserve(KEY, AuthCodePurpose.PASSWORD_RESET, NOW, NOW.minusSeconds(60));

        Instant later = NOW.plusSeconds(61);
        assertThat(repository.reserve(KEY, AuthCodePurpose.PASSWORD_RESET, later, later.minusSeconds(60))).isEmpty();
    }

    @Test
    void purposesAreIndependent() {
        repository.reserve(KEY, AuthCodePurpose.PASSWORD_RESET, NOW, NOW.minusSeconds(60));

        assertThat(repository.reserve(KEY, AuthCodePurpose.EMAIL_VERIFICATION, NOW, NOW.minusSeconds(60))).isEmpty();
    }

    @Test
    void recordStartsTheCooldownEvenWhenOneIsRunning() {
        repository.record(KEY, AuthCodePurpose.EMAIL_VERIFICATION, NOW);
        Instant later = NOW.plusSeconds(30);
        repository.record(KEY, AuthCodePurpose.EMAIL_VERIFICATION, later);

        Instant check = NOW.plusSeconds(70);
        assertThat(repository.reserve(KEY, AuthCodePurpose.EMAIL_VERIFICATION, check, check.minusSeconds(60)))
                .contains(later);
    }

    @Test
    void oldRowsArePurged() {
        repository.record(KEY, AuthCodePurpose.EMAIL_VERIFICATION, NOW.minusSeconds(90_000));
        repository.record("b".repeat(64), AuthCodePurpose.EMAIL_VERIFICATION, NOW);

        assertThat(repository.deleteOlderThan(NOW.minusSeconds(86_400))).isEqualTo(1);
    }
}
