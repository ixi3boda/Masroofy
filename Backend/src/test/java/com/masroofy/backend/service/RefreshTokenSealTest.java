package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;

import com.masroofy.backend.util.SecureCodes;
import java.security.SecureRandom;
import org.junit.jupiter.api.Test;

class RefreshTokenSealTest {

    private final RefreshTokenSeal seal = new RefreshTokenSeal(
            new SecureCodes("test-secret-test-secret-test-secret-123", new SecureRandom()));

    @Test
    void roundTripsVersionAndToken() {
        String sealed = seal.seal(3, "AMf-vBx_firebase-token");

        assertThat(sealed).startsWith("3.").endsWith(".AMf-vBx_firebase-token");
        assertThat(seal.unseal(sealed)).contains(new RefreshTokenSeal.Unsealed(3, "AMf-vBx_firebase-token"));
    }

    @Test
    void firebaseTokenMayContainDots() {
        assertThat(seal.unseal(seal.seal(0, "a.b.c"))).contains(new RefreshTokenSeal.Unsealed(0, "a.b.c"));
    }

    @Test
    void raisingTheVersionBreaksTheSeal() {
        String sealed = seal.seal(1, "token");

        assertThat(seal.unseal("9" + sealed.substring(1))).isEmpty();
    }

    @Test
    void swappingTheFirebaseTokenBreaksTheSeal() {
        String sealed = seal.seal(1, "token");

        assertThat(seal.unseal(sealed.substring(0, sealed.lastIndexOf('.') + 1) + "other")).isEmpty();
    }

    @Test
    void aSealFromAnotherSecretIsRejected() {
        RefreshTokenSeal other = new RefreshTokenSeal(
                new SecureCodes("another-secret-another-secret-12345", new SecureRandom()));

        assertThat(seal.unseal(other.seal(1, "token"))).isEmpty();
    }

    @Test
    void malformedValuesAreRejected() {
        for (String bad : new String[] {null, "", "token", "1.token", "x.abc.token", "-1.abc.token", "1.abc.",
                ".abc.token"}) {
            assertThat(seal.unseal(bad)).as(String.valueOf(bad)).isEmpty();
        }
    }

    @Test
    void toStringHidesTheToken() {
        assertThat(new RefreshTokenSeal.Unsealed(1, "secret-token").toString()).doesNotContain("secret-token");
    }
}
