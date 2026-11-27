package com.masroofy.backend.config;

import org.springframework.beans.factory.config.BeanPostProcessor;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.mail.javamail.JavaMailSenderImpl;

@Configuration
public class MailConfig {

    static final String GMAIL_HOST = "smtp.gmail.com";

    /**
     * Google displays App Passwords in groups ("abcd efgh ijkl mnop"); the real password has no spaces.
     * Strip them for Gmail so the value can be pasted exactly as shown.
     */
    @Bean
    public static BeanPostProcessor gmailAppPasswordNormalizer() {
        return new BeanPostProcessor() {
            @Override
            public Object postProcessAfterInitialization(Object bean, String beanName) {
                if (bean instanceof JavaMailSenderImpl sender) {
                    normalizeGmailPassword(sender);
                }
                return bean;
            }
        };
    }

    static void normalizeGmailPassword(JavaMailSenderImpl sender) {
        if (GMAIL_HOST.equalsIgnoreCase(sender.getHost()) && sender.getPassword() != null) {
            sender.setPassword(sender.getPassword().replaceAll("\\s+", ""));
        }
    }
}
