package com.masroofy.backend.service;

import com.masroofy.backend.util.EmailUtils;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.stereotype.Service;

/** Local development only (app.mail.provider=log): prints codes instead of emailing them. */
@Service
@ConditionalOnProperty(prefix = "app.mail", name = "provider", havingValue = "log")
public class LoggingEmailService implements EmailService {

    private static final Logger log = LoggerFactory.getLogger(LoggingEmailService.class);

    public LoggingEmailService() {
        log.warn("app.mail.provider=log: verification codes are written to the log. Never use this in production.");
    }

    @Override
    public void sendVerificationCode(String to, String fullName, String code, Duration validFor) {
        log.info("[DEV EMAIL] Verification code for {}: {} (valid {})", EmailUtils.mask(to), code, validFor);
    }

    @Override
    public void sendPasswordResetCode(String to, String fullName, String code, Duration validFor) {
        log.info("[DEV EMAIL] Password reset code for {}: {} (valid {})", EmailUtils.mask(to), code, validFor);
    }
}
