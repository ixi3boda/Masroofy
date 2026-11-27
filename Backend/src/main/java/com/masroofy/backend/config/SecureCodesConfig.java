package com.masroofy.backend.config;

import com.masroofy.backend.util.SecureCodes;
import java.security.SecureRandom;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class SecureCodesConfig {

    @Bean
    public SecureCodes secureCodes(AuthProperties properties) {
        return new SecureCodes(properties.codeSecret(), new SecureRandom());
    }
}
