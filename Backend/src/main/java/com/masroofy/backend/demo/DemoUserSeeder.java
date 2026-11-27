package com.masroofy.backend.demo;

import com.masroofy.backend.config.DemoProperties;
import com.masroofy.backend.config.DemoProperties.DemoUser;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.PasswordPolicy;
import com.masroofy.backend.util.EmailUtils;
import java.time.Clock;
import java.time.Instant;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Component;

/**
 * DEVELOPMENT ONLY (app.demo.enabled=true). At startup, makes every configured demo user exist in Firebase
 * (email verified, configured password) and in PostgreSQL, linked to each other, then reloads that user's demo data
 * so the dashboard always shows a full current month.
 */
@Component
@ConditionalOnProperty(prefix = "app.demo", name = "enabled", havingValue = "true")
public class DemoUserSeeder implements ApplicationRunner {

    private static final Logger log = LoggerFactory.getLogger(DemoUserSeeder.class);

    private final DemoProperties properties;
    private final FirebaseIdentityClient firebase;
    private final UserRepository userRepository;
    private final PasswordPolicy passwordPolicy;
    private final DemoLedgerLoader ledgerLoader;
    private final Clock clock;

    public DemoUserSeeder(DemoProperties properties, FirebaseIdentityClient firebase, UserRepository userRepository,
                          PasswordPolicy passwordPolicy, DemoLedgerLoader ledgerLoader, Clock clock) {
        this.properties = properties;
        this.firebase = firebase;
        this.userRepository = userRepository;
        this.passwordPolicy = passwordPolicy;
        this.ledgerLoader = ledgerLoader;
        this.clock = clock;
    }

    @Override
    public void run(ApplicationArguments args) {
        log.warn("app.demo.enabled=true: creating demo users and demo data. Never enable this in production.");
        for (DemoUser demoUser : properties.users()) {
            if (!demoUser.configured()) {
                continue;
            }
            if (demoUser.password() == null || demoUser.password().isBlank()) {
                log.warn("Skipping demo user {}: no password set (DEMO_USER_PASSWORD / DEMO_USER2_PASSWORD in .env)",
                        EmailUtils.mask(demoUser.email()));
                continue;
            }
            try {
                seed(demoUser);
            } catch (RuntimeException e) {
                // A demo account must never stop the API from starting; the reason is in the log.
                log.error("Could not prepare demo user {}: {}", EmailUtils.mask(demoUser.email()), describe(e), e);
            }
        }
    }

    /** Returns the PostgreSQL user that now holds fresh demo data. */
    User seed(DemoUser demoUser) {
        String email = EmailUtils.normalize(demoUser.email());
        String fullName = demoUser.fullName() == null || demoUser.fullName().isBlank()
                ? "Demo User" : demoUser.fullName().trim().replaceAll("\\s+", " ");
        if (demoUser.password() == null || demoUser.password().isBlank()) {
            throw new IllegalStateException("No password configured for this demo user");
        }
        passwordPolicy.validate("password", demoUser.password(), fullName, email);

        String uid = ensureFirebaseUser(email, demoUser.password(), fullName);
        User user = ensureDatabaseUser(email, fullName, uid);
        int written = ledgerLoader.load(user.id());
        log.info("Demo user {} is ready with {} transactions", EmailUtils.mask(email), written);
        return user;
    }

    private String ensureFirebaseUser(String email, String password, String fullName) {
        String uid = firebase.findUidByEmail(email).orElse(null);
        if (uid == null) {
            uid = firebase.createUser(email, password, fullName);
            log.info("Created Firebase user for demo account {}", EmailUtils.mask(email));
        } else if (!passwordWorks(email, password)) {
            // Only when needed: a password change signs the account out on every device.
            firebase.updatePassword(uid, password);
            log.info("Reset the Firebase password of demo account {} to the configured one", EmailUtils.mask(email));
        }
        firebase.markEmailVerified(uid);
        return uid;
    }

    private boolean passwordWorks(String email, String password) {
        try {
            firebase.signInWithPassword(email, password);
            return true;
        } catch (ApiException e) {
            if (e.getErrorCode() == ErrorCode.INVALID_CREDENTIALS) {
                return false;
            }
            throw e;
        }
    }

    private User ensureDatabaseUser(String email, String fullName, String uid) {
        Instant now = clock.instant();
        return userRepository.findByEmail(email).map(found -> {
            if (!found.firebaseUid().equals(uid)) {
                userRepository.relinkFirebaseUid(found.id(), uid, now);
            }
            if (!found.isEmailVerified()) {
                userRepository.markEmailVerified(found.id(), now);
            }
            return found;
        }).orElseGet(() -> {
            User created = new User(UUID.randomUUID(), uid, email, null, fullName, User.DEFAULT_CURRENCY,
                    User.DEFAULT_LOCALE, User.DEFAULT_TIMEZONE, null, now, now, now, now);
            userRepository.insert(created);
            return created;
        });
    }

    private static String describe(RuntimeException e) {
        return e instanceof ApiException api ? api.getErrorCode() + " " + api.getMessage() : e.getMessage();
    }
}
