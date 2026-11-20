package com.financeapp.sms.config;

import com.financeapp.sms.parser.SmsParser;
import java.io.IOException;
import java.io.InputStream;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
@EnableConfigurationProperties(SmsProperties.class)
public class SmsConfig {

    /** Loads src/main/resources/sms/sms-model.tsv.gz once at startup (~0.3 s, ~60 MB heap). */
    @Bean
    public SmsParser smsParser() throws IOException {
        try (InputStream in = SmsConfig.class.getResourceAsStream("/sms/sms-model.tsv.gz")) {
            if (in == null) throw new IllegalStateException("Missing resource /sms/sms-model.tsv.gz");
            return SmsParser.load(in);
        }
    }
}
