package com.masroofy.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties(prefix = "app.firebase")
public record FirebaseProperties(
        String credentialsPath,
        String credentialsBase64,
        String projectId,
        String webApiKey,
        @DefaultValue("true") boolean checkRevoked,
        @DefaultValue("https://identitytoolkit.googleapis.com") String identityToolkitBaseUrl,
        @DefaultValue("https://securetoken.googleapis.com") String secureTokenBaseUrl) {
}
