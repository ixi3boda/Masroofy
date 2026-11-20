package com.masroofy.backend.config;

import io.swagger.v3.oas.annotations.OpenAPIDefinition;
import io.swagger.v3.oas.annotations.enums.SecuritySchemeType;
import io.swagger.v3.oas.annotations.info.Info;
import io.swagger.v3.oas.annotations.security.SecurityScheme;
import org.springframework.context.annotation.Configuration;

/**
 * Swagger UI at /swagger-ui.html, OpenAPI JSON at /v3/api-docs.
 * Click "Authorize" and paste the accessToken from /api/v1/auth/login to call protected endpoints.
 */
@Configuration
@OpenAPIDefinition(info = @Info(
        title = "Masroofy API",
        version = "v1",
        description = """
                Backend for the Masroofy budgeting app. Every error uses the same body (ErrorResponse); \
                switch on its `code` field. Timestamps are ISO-8601 UTC."""))
@SecurityScheme(
        name = OpenApiConfig.BEARER_AUTH,
        type = SecuritySchemeType.HTTP,
        scheme = "bearer",
        bearerFormat = "Firebase ID token",
        description = "The accessToken returned by /api/v1/auth/login or /api/v1/auth/token/refresh")
public class OpenApiConfig {

    public static final String BEARER_AUTH = "bearerAuth";
}
