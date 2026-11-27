package com.masroofy.backend.config;

import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

@ConfigurationProperties(prefix = "app.mail")
public record MailProperties(
        @DefaultValue("smtp") String provider,
        String from,
        @DefaultValue("Masroofy") String fromName) {
}
