package com.masroofy.backend.config;

import java.time.Clock;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

@Configuration
public class ClockConfig {

    /** All timestamps are UTC (entity doc convention). Injected so time can be fixed in tests. */
    @Bean
    public Clock clock() {
        return Clock.systemUTC();
    }
}
