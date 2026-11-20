package com.masroofy.backend.config;

import com.google.auth.oauth2.GoogleCredentials;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.auth.FirebaseAuth;
import java.io.ByteArrayInputStream;
import java.io.FileInputStream;
import java.io.IOException;
import java.io.InputStream;
import java.util.Base64;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.util.StringUtils;
import org.springframework.web.client.RestClient;

@Configuration
public class FirebaseConfig {

    private static final Logger log = LoggerFactory.getLogger(FirebaseConfig.class);

    @Bean
    public FirebaseApp firebaseApp(FirebaseProperties properties) throws IOException {
        if (!FirebaseApp.getApps().isEmpty()) {
            return FirebaseApp.getInstance();
        }
        FirebaseOptions.Builder options = FirebaseOptions.builder().setCredentials(loadCredentials(properties));
        if (StringUtils.hasText(properties.projectId())) {
            options.setProjectId(properties.projectId());
        }
        FirebaseApp app = FirebaseApp.initializeApp(options.build());
        log.info("Firebase initialised for project {}", app.getOptions().getProjectId());
        return app;
    }

    @Bean
    public FirebaseAuth firebaseAuth(FirebaseApp firebaseApp) {
        return FirebaseAuth.getInstance(firebaseApp);
    }

    /** Client for the Firebase Auth REST API (password sign-in and token refresh). */
    @Bean
    public RestClient firebaseRestClient(RestClient.Builder builder, FirebaseProperties properties) {
        if (!StringUtils.hasText(properties.webApiKey())) {
            throw new IllegalStateException("app.firebase.web-api-key (FIREBASE_WEB_API_KEY) must be set");
        }
        return builder
                .defaultHeader("X-Goog-Api-Key", properties.webApiKey())
                .build();
    }

    private GoogleCredentials loadCredentials(FirebaseProperties properties) throws IOException {
        if (StringUtils.hasText(properties.credentialsBase64())) {
            byte[] json = Base64.getDecoder().decode(properties.credentialsBase64().trim());
            return GoogleCredentials.fromStream(new ByteArrayInputStream(json));
        }
        if (StringUtils.hasText(properties.credentialsPath())) {
            try (InputStream in = new FileInputStream(properties.credentialsPath())) {
                return GoogleCredentials.fromStream(in);
            }
        }
        return GoogleCredentials.getApplicationDefault();
    }
}
