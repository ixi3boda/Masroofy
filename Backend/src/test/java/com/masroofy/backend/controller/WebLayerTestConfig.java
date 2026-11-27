package com.masroofy.backend.controller;

import com.masroofy.backend.config.ClockConfig;
import com.masroofy.backend.config.CorsProperties;
import com.masroofy.backend.config.FirebaseProperties;
import com.masroofy.backend.config.SecurityConfig;
import com.masroofy.backend.security.ErrorResponseWriter;
import org.springframework.boot.context.properties.EnableConfigurationProperties;
import org.springframework.boot.test.context.TestConfiguration;
import org.springframework.context.annotation.Import;

/** The real security setup, loaded into @WebMvcTest slices. */
@TestConfiguration
@Import({SecurityConfig.class, ErrorResponseWriter.class, ClockConfig.class})
@EnableConfigurationProperties({FirebaseProperties.class, CorsProperties.class})
public class WebLayerTestConfig {
}
