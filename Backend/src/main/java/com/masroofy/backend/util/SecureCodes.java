package com.masroofy.backend.util;

import java.nio.charset.StandardCharsets;
import java.security.InvalidKeyException;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.security.SecureRandom;
import java.util.Base64;
import java.util.HexFormat;
import javax.crypto.Mac;
import javax.crypto.spec.SecretKeySpec;

/** Generates one-time codes and tokens and hashes them with HMAC-SHA256 before storage. */
public final class SecureCodes {

    private static final String HMAC = "HmacSHA256";

    private final SecureRandom random;
    private final SecretKeySpec key;

    public SecureCodes(String secret, SecureRandom random) {
        this.random = random;
        this.key = new SecretKeySpec(secret.getBytes(StandardCharsets.UTF_8), HMAC);
    }

    /** A numeric code of {@code length} digits; leading zeros are kept. */
    public String numericCode(int length) {
        StringBuilder code = new StringBuilder(length);
        for (int i = 0; i < length; i++) {
            code.append(random.nextInt(10));
        }
        return code.toString();
    }

    /** A 256-bit URL-safe random token. */
    public String token() {
        byte[] bytes = new byte[32];
        random.nextBytes(bytes);
        return Base64.getUrlEncoder().withoutPadding().encodeToString(bytes);
    }

    /** Hex-encoded HMAC-SHA256 of the value (64 characters). */
    public String hash(String value) {
        try {
            Mac mac = Mac.getInstance(HMAC);
            mac.init(key);
            return HexFormat.of().formatHex(mac.doFinal(value.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException | InvalidKeyException e) {
            throw new IllegalStateException("HMAC-SHA256 unavailable", e);
        }
    }

    /** Constant-time comparison of a candidate value against a stored hash. */
    public boolean matches(String candidate, String storedHash) {
        if (candidate == null || storedHash == null) {
            return false;
        }
        return MessageDigest.isEqual(
                hash(candidate).getBytes(StandardCharsets.US_ASCII),
                storedHash.getBytes(StandardCharsets.US_ASCII));
    }
}
