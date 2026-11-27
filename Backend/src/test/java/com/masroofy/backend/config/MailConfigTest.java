package com.masroofy.backend.config;

import static org.assertj.core.api.Assertions.assertThat;

import org.junit.jupiter.api.Test;
import org.springframework.mail.javamail.JavaMailSenderImpl;

class MailConfigTest {

    private static JavaMailSenderImpl sender(String host, String password) {
        JavaMailSenderImpl sender = new JavaMailSenderImpl();
        sender.setHost(host);
        sender.setPassword(password);
        MailConfig.gmailAppPasswordNormalizer().postProcessAfterInitialization(sender, "mailSender");
        return sender;
    }

    @Test
    void stripsSpacesFromGmailAppPasswords() {
        assertThat(sender("smtp.gmail.com", "abcd efgh ijkl mnop").getPassword()).isEqualTo("abcdefghijklmnop");
    }

    @Test
    void leavesOtherProvidersUntouched() {
        assertThat(sender("smtp.office365.com", "pass with spaces").getPassword()).isEqualTo("pass with spaces");
    }
}
