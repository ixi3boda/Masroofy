package com.masroofy.backend.config;

import java.time.Duration;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties(prefix = "app.auth")
public record AuthProperties(
        String codeSecret,
        @DefaultValue("6") int codeLength,
        @DefaultValue("10m") Duration codeTtl,
        @DefaultValue("5") int maxCodeAttempts,
        @DefaultValue("60s") Duration resendCooldown,
        @DefaultValue("15m") Duration resetTokenTtl) {

    public AuthProperties {
        if (codeSecret == null || codeSecret.length() < 32) {
            throw new IllegalStateException(
                    "app.auth.code-secret (AUTH_CODE_SECRET) must be set and at least 32 characters long");
        }
        if (codeLength < 4 || codeLength > 10) {
            throw new IllegalStateException("app.auth.code-length must be between 4 and 10");
        }
        if (maxCodeAttempts < 1) {
            throw new IllegalStateException("app.auth.max-code-attempts must be at least 1");
        }
    }
}
