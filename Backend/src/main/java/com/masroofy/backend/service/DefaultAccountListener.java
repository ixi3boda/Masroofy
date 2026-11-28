package com.masroofy.backend.service;

import com.masroofy.backend.util.EmailUtils;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.event.EventListener;
import org.springframework.stereotype.Component;

/**
 * Gives every new sign-up a "Cash" account, so Add Transaction has an account to record against from the start.
 * A failure here never fails the sign-up (the event is published after the sign-up is committed); it is logged.
 */
@Component
public class DefaultAccountListener {

    private static final Logger log = LoggerFactory.getLogger(DefaultAccountListener.class);

    private final AccountService accountService;

    public DefaultAccountListener(AccountService accountService) {
        this.accountService = accountService;
    }

    @EventListener
    public void onUserRegistered(UserRegisteredEvent event) {
        try {
            accountService.createDefaultCash(event.userId());
        } catch (RuntimeException e) {
            log.warn("Could not create the default Cash account for {}: {}", EmailUtils.mask(event.email()),
                    e.getMessage());
        }
    }
}
