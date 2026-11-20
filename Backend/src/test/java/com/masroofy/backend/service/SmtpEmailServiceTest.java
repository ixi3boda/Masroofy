package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.masroofy.backend.config.MailProperties;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import jakarta.mail.Session;
import jakarta.mail.internet.InternetAddress;
import jakarta.mail.internet.MimeMessage;
import java.time.Duration;
import java.util.Properties;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.mail.MailSendException;
import org.springframework.mail.javamail.JavaMailSender;

class SmtpEmailServiceTest {

    private final JavaMailSender sender = mock(JavaMailSender.class);

    private static org.springframework.boot.autoconfigure.mail.MailProperties smtp(String user, String password) {
        var smtp = new org.springframework.boot.autoconfigure.mail.MailProperties();
        smtp.setHost("smtp.gmail.com");
        smtp.setUsername(user);
        smtp.setPassword(password);
        return smtp;
    }

    private SmtpEmailService service(String from) {
        when(sender.createMimeMessage()).thenReturn(new MimeMessage(Session.getInstance(new Properties())));
        return new SmtpEmailService(sender, new MailProperties("smtp", from, "Masroofy"),
                smtp("owner@gmail.com", "app-password"));
    }

    private MimeMessage sentMessage() {
        ArgumentCaptor<MimeMessage> message = ArgumentCaptor.forClass(MimeMessage.class);
        verify(sender).send(message.capture());
        return message.getValue();
    }

    @Test
    void sendsFromTheSmtpAccountWhenNoFromIsConfigured() throws Exception {
        service("").sendVerificationCode("mariam@example.com", "Mariam", "042517", Duration.ofMinutes(10));

        MimeMessage message = sentMessage();
        InternetAddress from = (InternetAddress) message.getFrom()[0];
        assertThat(from.getAddress()).isEqualTo("owner@gmail.com");
        assertThat(from.getPersonal()).isEqualTo("Masroofy");
        assertThat(message.getAllRecipients()[0].toString()).isEqualTo("mariam@example.com");
        assertThat(message.getSubject()).isEqualTo("Your Masroofy verification code");
    }

    @Test
    void explicitFromAddressWins() throws Exception {
        service("alias@masroofy.app").sendPasswordResetCode("m@example.com", "M", "123456", Duration.ofMinutes(10));

        assertThat(((InternetAddress) sentMessage().getFrom()[0]).getAddress()).isEqualTo("alias@masroofy.app");
    }

    @Test
    void deliveryFailureBecomesEmailDeliveryFailed() {
        SmtpEmailService service = service("");
        doThrow(new MailSendException("535 Username and Password not accepted")).when(sender).send(any(MimeMessage.class));

        assertThatThrownBy(() -> service.sendVerificationCode("m@example.com", "M", "1", Duration.ofMinutes(10)))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.EMAIL_DELIVERY_FAILED));
    }

    @Test
    void refusesToStartWithoutCredentials() {
        assertThatThrownBy(() -> new SmtpEmailService(sender, new MailProperties("smtp", "", "Masroofy"),
                smtp("owner@gmail.com", "")))
                .isInstanceOf(IllegalStateException.class)
                .hasMessageContaining("MAIL_PASSWORD");
    }
}
