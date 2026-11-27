package com.masroofy.backend.util;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;

class EmailUtilsTest {

    @Test
    void normalizeTrimsAndLowerCases() {
        assertThat(EmailUtils.normalize("  Mariam.Ali@Example.COM ")).isEqualTo("mariam.ali@example.com");
        assertThat(EmailUtils.normalize(null)).isNull();
    }

    @Test
    void maskKeepsFirstLetterAndDomainLikeTheVerificationScreens() {
        assertThat(EmailUtils.mask("mariam@example.com")).isEqualTo("m***@example.com");
        assertThat(EmailUtils.mask("a@example.com")).isEqualTo("a***@example.com");
    }

    @Test
    void maskHandlesMalformedInput() {
        assertThat(EmailUtils.mask("@example.com")).isEqualTo("***");
        assertThat(EmailUtils.mask("no-at-sign")).isEqualTo("***");
        assertThat(EmailUtils.mask(null)).isNull();
    }
}
