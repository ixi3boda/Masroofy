package com.masroofy.backend.service;

import com.masroofy.backend.util.SecureCodes;
import java.util.Optional;
import org.springframework.stereotype.Component;

/**
 * Binds each Firebase refresh token the app receives to the user's session version, so a refresh token issued
 * before a logout or password reset can be refused even when Firebase's own (whole-second) revocation misses it.
 * <p>
 * Format sent to the app: {@code <sessionVersion>.<HMAC-SHA256 hex>.<Firebase refresh token>}. The app treats it
 * as an opaque string. The HMAC (key {@code AUTH_CODE_SECRET}) stops a client from raising the version.
 */
@Component
public class RefreshTokenSeal {

    public record Unsealed(int sessionVersion, String firebaseToken) {
        @Override
        public String toString() {
            return "Unsealed[sessionVersion=" + sessionVersion + ", firebaseToken=***]";
        }
    }

    private final SecureCodes secureCodes;

    public RefreshTokenSeal(SecureCodes secureCodes) {
        this.secureCodes = secureCodes;
    }

    public String seal(int sessionVersion, String firebaseToken) {
        return sessionVersion + "." + secureCodes.hash(payload(sessionVersion, firebaseToken)) + "." + firebaseToken;
    }

    /** Empty when the value is not a sealed token or was altered. */
    public Optional<Unsealed> unseal(String sealed) {
        if (sealed == null) {
            return Optional.empty();
        }
        int first = sealed.indexOf('.');
        int second = first < 0 ? -1 : sealed.indexOf('.', first + 1);
        if (first <= 0 || second < 0 || second == sealed.length() - 1) {
            return Optional.empty();
        }
        int version;
        try {
            version = Integer.parseInt(sealed.substring(0, first));
        } catch (NumberFormatException e) {
            return Optional.empty();
        }
        String mac = sealed.substring(first + 1, second);
        String firebaseToken = sealed.substring(second + 1);
        if (version < 0 || !secureCodes.matches(payload(version, firebaseToken), mac)) {
            return Optional.empty();
        }
        return Optional.of(new Unsealed(version, firebaseToken));
    }

    private static String payload(int sessionVersion, String firebaseToken) {
        return "refresh-token:" + sessionVersion + ":" + firebaseToken;
    }
}
