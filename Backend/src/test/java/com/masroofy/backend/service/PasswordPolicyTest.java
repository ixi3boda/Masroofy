package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.service.PasswordPolicy.Rule;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;

class PasswordPolicyTest {

    private static final String NAME = "Mariam Ali";
    private static final String EMAIL = "mariam.ali@example.com";

    private final PasswordPolicy policy = new PasswordPolicy();

    @ParameterizedTest
    @ValueSource(strings = {"Sunny-Nile9", "kofta#lover", "kite-runner-71", "blue horse 7"})
    void acceptsPasswordsMeetingEveryRequirement(String password) {
        assertThat(policy.check(password, NAME, EMAIL)).isEmpty();
    }

    @Test
    void rejectsShortPasswords() {
        assertThat(policy.check("Ab1!", NAME, EMAIL)).containsExactly(Rule.MIN_LENGTH);
    }

    @Test
    void rejectsOverlyLongPasswords() {
        assertThat(policy.check("a1".repeat(65), NAME, EMAIL)).containsExactly(Rule.MAX_LENGTH);
    }

    @Test
    void requiresANumberOrSymbol() {
        assertThat(policy.check("OnlyLetters", NAME, EMAIL)).containsExactly(Rule.NUMBER_OR_SYMBOL);
        assertThat(policy.check("letters and spaces", NAME, EMAIL)).containsExactly(Rule.NUMBER_OR_SYMBOL);
    }

    @ParameterizedTest
    @ValueSource(strings = {"MARIAM2024!", "xx-ali-xx-9", "mariam.ali#1"})
    void rejectsPasswordsContainingNameOrEmail(String password) {
        assertThat(policy.check(password, NAME, EMAIL)).containsExactly(Rule.NO_PERSONAL_INFO);
    }

    /** The common / easily guessed password rule was removed: these now pass. */
    @ParameterizedTest
    @ValueSource(strings = {"12345678", "87654321", "!!!!!!!!", "password1", "Password123!", "P@ssw0rd",
            "Qwerty123!", "qwertyuiop1", "1q2w3e4r", "Football#1"})
    void acceptsCommonOrEasilyGuessedPasswords(String password) {
        assertThat(policy.check(password, NAME, EMAIL)).isEmpty();
    }

    @Test
    void shortPasswordsOnlyReportTheLengthRules() {
        assertThat(policy.check("1234567", NAME, EMAIL)).containsExactly(Rule.MIN_LENGTH);
    }

    @Test
    void ignoresVeryShortNameParts() {
        assertThat(policy.check("go-al-2024", "Al Go", "x@example.com")).isEmpty();
    }

    @Test
    void reportsEveryFailedRuleAtOnce() {
        assertThat(policy.check("ali", NAME, EMAIL))
                .containsExactly(Rule.MIN_LENGTH, Rule.NUMBER_OR_SYMBOL, Rule.NO_PERSONAL_INFO);
    }

    @Test
    void validateThrowsWeakPasswordWithFieldErrors() {
        assertThatThrownBy(() -> policy.validate("newPassword", "short", NAME, EMAIL))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.getErrorCode()).isEqualTo(ErrorCode.WEAK_PASSWORD);
                    assertThat(e.getFieldErrors()).extracting("field").containsOnly("newPassword");
                    assertThat(e.getFieldErrors()).extracting("code")
                            .containsExactly("MIN_LENGTH", "NUMBER_OR_SYMBOL");
                });
    }

    @Test
    void validatePassesSilentlyForGoodPassword() {
        policy.validate("password", "Sunny-Nile9", NAME, EMAIL);
    }
}
