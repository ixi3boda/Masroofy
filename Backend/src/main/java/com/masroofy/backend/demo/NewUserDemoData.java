package com.masroofy.backend.demo;

import com.masroofy.backend.service.UserRegisteredEvent;
import com.masroofy.backend.util.EmailUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * DEVELOPMENT ONLY (app.demo.for-new-users=true). Gives every new sign-up the demo data, so their dashboard is full
 * right after they verify their email and log in. A failure here never fails the sign-up.
 */
@Component
@ConditionalOnProperty(prefix = "app.demo", name = "for-new-users", havingValue = "true")
public class NewUserDemoData {

    private static final Logger log = LoggerFactory.getLogger(NewUserDemoData.class);

    private final DemoLedgerLoader ledgerLoader;

    public NewUserDemoData(DemoLedgerLoader ledgerLoader) {
        this.ledgerLoader = ledgerLoader;
    }

    @EventListener
    public void onUserRegistered(UserRegisteredEvent event) {
        try {
            int written = ledgerLoader.load(event.userId());
            log.info("Loaded demo data for new user {} ({} transactions)", EmailUtils.mask(event.email()), written);
        } catch (RuntimeException e) {
            log.warn("Could not load demo data for new user {}: {}", EmailUtils.mask(event.email()), e.getMessage());
        }
    }
}
