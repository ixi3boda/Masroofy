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

    private final PasswordPolicy policy = new PasswordPolicy();

    @ParameterizedTest
    @ValueSource(strings = {"Sunny-Nile9", "Kofta#lover", "kite-Runner-71", "blue horse 7Z", "Ωmega-2026"})
    void acceptsPasswordsMeetingEveryRequirement(String password) {
        assertThat(policy.check(password)).isEmpty();
    }

    @Test
    void rejectsShortPasswords() {
        assertThat(policy.check("Ab1!")).containsExactly(Rule.MIN_LENGTH);
    }

    @Test
    void rejectsOverlyLongPasswords() {
        assertThat(policy.check("A1".repeat(65))).containsExactly(Rule.MAX_LENGTH);
    }

    @Test
    void requiresANumberOrSymbol() {
        assertThat(policy.check("OnlyLetters")).containsExactly(Rule.NUMBER_OR_SYMBOL);
        assertThat(policy.check("Letters and spaces")).containsExactly(Rule.NUMBER_OR_SYMBOL);
    }

    @ParameterizedTest
    @ValueSource(strings = {"lowercase-only1", "12345678", "!!!!!!!!", "ünïcode-123"})
    void requiresAnUppercaseLetter(String password) {
        assertThat(policy.check(password)).containsExactly(Rule.UPPERCASE);
    }

    /** The name/email rule was removed: a password may contain the user's name or email. */
    @ParameterizedTest
    @ValueSource(strings = {"MARIAM2024!", "Xx-ali-xx-9", "Mariam.ali#1"})
    void acceptsPasswordsContainingNameOrEmail(String password) {
        assertThat(policy.check(password)).isEmpty();
    }

    /** The common / easily guessed password rule was removed: these now pass. */
    @ParameterizedTest
    @ValueSource(strings = {"Password1", "Password123!", "P@ssw0rd", "Qwerty123!", "Qwertyuiop1", "1Q2w3e4r",
            "Football#1", "ABCD1234"})
    void acceptsCommonOrEasilyGuessedPasswords(String password) {
        assertThat(policy.check(password)).isEmpty();
    }

    @Test
    void shortPasswordsOnlyReportTheLengthRules() {
        assertThat(policy.check("ABC1234")).containsExactly(Rule.MIN_LENGTH);
    }

    @Test
    void reportsEveryFailedRuleAtOnce() {
        assertThat(policy.check("ali")).containsExactly(Rule.MIN_LENGTH, Rule.NUMBER_OR_SYMBOL, Rule.UPPERCASE);
    }

    @Test
    void validateThrowsWeakPasswordWithFieldErrors() {
        assertThatThrownBy(() -> policy.validate("newPassword", "short"))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.getErrorCode()).isEqualTo(ErrorCode.WEAK_PASSWORD);
                    assertThat(e.getFieldErrors()).extracting("field").containsOnly("newPassword");
                    assertThat(e.getFieldErrors()).extracting("code")
                            .containsExactly("MIN_LENGTH", "NUMBER_OR_SYMBOL", "UPPERCASE");
                });
    }

    @Test
    void validatePassesSilentlyForGoodPassword() {
        policy.validate("password", "Sunny-Nile9");
    }
}
