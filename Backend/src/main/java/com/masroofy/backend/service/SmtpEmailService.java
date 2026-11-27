package com.masroofy.backend.service;

import com.masroofy.backend.config.MailProperties;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import jakarta.mail.MessagingException;
import jakarta.mail.internet.MimeMessage;
import java.io.UnsupportedEncodingException;
import java.time.Duration;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.autoconfigure.condition.ConditionalOnProperty;
import org.springframework.mail.MailException;
import org.springframework.mail.javamail.JavaMailSender;
import org.springframework.mail.javamail.MimeMessageHelper;
import org.springframework.stereotype.Service;
import org.springframework.util.StringUtils;
import org.springframework.web.util.HtmlUtils;

@Service
@ConditionalOnProperty(prefix = "app.mail", name = "provider", havingValue = "smtp", matchIfMissing = true)
public class SmtpEmailService implements EmailService {

    private static final Logger log = LoggerFactory.getLogger(SmtpEmailService.class);

    private final JavaMailSender mailSender;
    private final MailProperties properties;
    private final String fromAddress;

    public SmtpEmailService(JavaMailSender mailSender, MailProperties properties,
                            org.springframework.boot.autoconfigure.mail.MailProperties smtp) {
        if (!StringUtils.hasText(smtp.getHost()) || !StringUtils.hasText(smtp.getUsername())
                || !StringUtils.hasText(smtp.getPassword())) {
            throw new IllegalStateException("MAIL_PROVIDER=smtp needs MAIL_HOST, MAIL_USERNAME and MAIL_PASSWORD. "
                    + "For Gmail use an App Password; or set MAIL_PROVIDER=log for local development.");
        }
        this.mailSender = mailSender;
        this.properties = properties;
        // Gmail (and most providers) only send as the authenticated account, so default to it.
        this.fromAddress = StringUtils.hasText(properties.from()) ? properties.from() : smtp.getUsername();
        log.info("Emails will be sent through {} as {}", smtp.getHost(), fromAddress);
    }

    @Override
    public void sendVerificationCode(String to, String fullName, String code, Duration validFor) {
        send(to, "Your Masroofy verification code",
                fullName,
                "Use this code to verify your email and finish creating your Masroofy account.",
                code, validFor);
    }

    @Override
    public void sendPasswordResetCode(String to, String fullName, String code, Duration validFor) {
        send(to, "Reset your Masroofy password",
                fullName,
                "Use this code to reset your Masroofy password. If you did not ask for this, you can ignore this email.",
                code, validFor);
    }

    private void send(String to, String subject, String fullName, String intro, String code, Duration validFor) {
        long minutes = Math.max(1, validFor.toMinutes());
        String greeting = "Hi " + fullName + ",";
        String text = greeting + "\n\n" + intro + "\n\n" + code + "\n\nThis code expires in " + minutes
                + " minutes. Never share it with anyone.\n\nMasroofy";
        String html = """
                <div style="font-family:Arial,sans-serif;max-width:480px;margin:auto;color:#1a1a2e">
                  <h2 style="color:#1f5eff">Masroofy</h2>
                  <p>%s</p>
                  <p>%s</p>
                  <p style="font-size:32px;font-weight:bold;letter-spacing:8px;margin:24px 0">%s</p>
                  <p>This code expires in %d minutes. Never share it with anyone.</p>
                </div>
                """.formatted(HtmlUtils.htmlEscape(greeting), HtmlUtils.htmlEscape(intro), code, minutes);
        try {
            MimeMessage message = mailSender.createMimeMessage();
            MimeMessageHelper helper = new MimeMessageHelper(message, true, "UTF-8");
            helper.setFrom(fromAddress, properties.fromName());
            helper.setTo(to);
            helper.setSubject(subject);
            helper.setText(text, html);
            mailSender.send(message);
        } catch (MailException | MessagingException | UnsupportedEncodingException e) {
            log.error("Failed to send '{}' email", subject, e);
            throw new ApiException(ErrorCode.EMAIL_DELIVERY_FAILED, e);
        }
    }
}
