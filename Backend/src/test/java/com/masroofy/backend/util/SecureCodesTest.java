package com.masroofy.backend.util;

import static org.assertj.core.api.Assertions.assertThat;

import java.security.SecureRandom;
import org.junit.jupiter.api.Test;

class SecureCodesTest {

    private final SecureCodes codes = new SecureCodes("test-secret-test-secret-test-secret-123", new SecureRandom());

    @Test
    void numericCodeHasRequestedLengthAndOnlyDigits() {
        for (int i = 0; i < 200; i++) {
            assertThat(codes.numericCode(6)).hasSize(6).containsOnlyDigits();
        }
    }

    @Test
    void tokenIsUrlSafeAndUnique() {
        String first = codes.token();
        assertThat(first).hasSize(43).matches("[A-Za-z0-9_-]+");
        assertThat(codes.token()).isNotEqualTo(first);
    }

    @Test
    void hashIsDeterministicHexAndDependsOnSecret() {
        String hash = codes.hash("123456");
        assertThat(hash).hasSize(64).matches("[0-9a-f]+").isEqualTo(codes.hash("123456"));
        SecureCodes other = new SecureCodes("another-secret-another-secret-12345", new SecureRandom());
        assertThat(other.hash("123456")).isNotEqualTo(hash);
    }

    @Test
    void matchesComparesAgainstStoredHash() {
        String stored = codes.hash("042517");
        assertThat(codes.matches("042517", stored)).isTrue();
        assertThat(codes.matches("042518", stored)).isFalse();
        assertThat(codes.matches(null, stored)).isFalse();
        assertThat(codes.matches("042517", null)).isFalse();
    }
}
