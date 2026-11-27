package com.masroofy.backend.config;

import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/**
 * Demo data for development (app.demo.*). Off by default so it can never run against production by accident.
 *
 * @param enabled     create or update {@code users} in Firebase and PostgreSQL at startup and reload their demo data
 * @param forNewUsers also give every new sign-up the demo data
 * @param users       demo accounts; entries without an email are ignored
 */
@ConfigurationProperties(prefix = "app.demo")
public record DemoProperties(
        @DefaultValue("false") boolean enabled,
        @DefaultValue("false") boolean forNewUsers,
        @DefaultValue List<DemoUser> users) {

    public record DemoUser(String email, String password, String fullName) {

        public boolean configured() {
            return email != null && !email.isBlank();
        }

        @Override
        public String toString() {
            return "DemoUser[email=" + email + ", password=***, fullName=" + fullName + "]";
        }
    }
}
