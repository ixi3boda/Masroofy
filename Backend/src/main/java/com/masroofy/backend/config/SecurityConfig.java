package com.masroofy.backend.config;

import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.security.ErrorResponseWriter;
import com.masroofy.backend.security.FirebaseTokenFilter;
import java.util.ArrayList;
import java.util.List;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.http.HttpMethod;
import org.springframework.security.config.annotation.web.builders.HttpSecurity;
import org.springframework.security.config.annotation.web.configuration.EnableWebSecurity;
import org.springframework.security.config.annotation.web.configurers.AbstractHttpConfigurer;
import org.springframework.security.config.http.SessionCreationPolicy;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.SecurityFilterChain;
import org.springframework.security.web.authentication.UsernamePasswordAuthenticationFilter;
import org.springframework.security.web.firewall.RequestRejectedHandler;
import org.springframework.security.web.servlet.util.matcher.PathPatternRequestMatcher;
import org.springframework.security.web.util.matcher.OrRequestMatcher;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.web.cors.CorsConfiguration;
import org.springframework.web.cors.CorsConfigurationSource;
import org.springframework.web.cors.UrlBasedCorsConfigurationSource;

@Configuration
@EnableWebSecurity
public class SecurityConfig {

    /** Endpoints reachable without a token (every auth screen before the user is logged in). */
    static final List<String> PUBLIC_AUTH_POSTS = List.of(
            "/api/v1/auth/register",
            "/api/v1/auth/login",
            "/api/v1/auth/token/refresh",
            "/api/v1/auth/email-verification/verify",
            "/api/v1/auth/email-verification/resend",
            "/api/v1/auth/password/forgot",
            "/api/v1/auth/password/verify-code",
            "/api/v1/auth/password/reset");

    @Bean
    public SecurityFilterChain securityFilterChain(HttpSecurity http, FirebaseIdentityClient firebase,
                                                   UserRepository userRepository, ErrorResponseWriter errorWriter,
                                                   FirebaseProperties firebaseProperties) throws Exception {
        RequestMatcher publicEndpoints = publicEndpoints();
        // Created here rather than as a @Bean so Spring Boot does not also register it as a servlet filter.
        FirebaseTokenFilter tokenFilter = new FirebaseTokenFilter(firebase, userRepository, errorWriter,
                publicEndpoints, firebaseProperties.checkRevoked());

        http
                .csrf(AbstractHttpConfigurer::disable)
                .cors(cors -> { })
                .httpBasic(AbstractHttpConfigurer::disable)
                .formLogin(AbstractHttpConfigurer::disable)
                .logout(AbstractHttpConfigurer::disable)
                .sessionManagement(session -> session.sessionCreationPolicy(SessionCreationPolicy.STATELESS))
                .authorizeHttpRequests(auth -> auth
                        .requestMatchers(publicEndpoints).permitAll()
                        .requestMatchers(HttpMethod.POST, "/api/v1/auth/logout").authenticated()
                        .anyRequest().hasAuthority(FirebaseTokenFilter.ROLE_USER))
                .exceptionHandling(ex -> ex
                        .authenticationEntryPoint((request, response, e) ->
                                errorWriter.write(request, response, ErrorCode.UNAUTHORIZED,
                                        ErrorCode.UNAUTHORIZED.defaultMessage()))
                        .accessDeniedHandler((request, response, e) -> {
                            Authentication authentication = SecurityContextHolder.getContext().getAuthentication();
                            boolean unverified = authentication != null && authentication.getAuthorities().stream()
                                    .anyMatch(a -> FirebaseTokenFilter.ROLE_UNVERIFIED.equals(a.getAuthority()));
                            ErrorCode code = unverified ? ErrorCode.EMAIL_NOT_VERIFIED : ErrorCode.FORBIDDEN;
                            errorWriter.write(request, response, code, code.defaultMessage());
                        }))
                .addFilterBefore(tokenFilter, UsernamePasswordAuthenticationFilter.class);
        return http.build();
    }

    /**
     * URLs refused by Spring Security's firewall ({@code //}, {@code %2e%2e}, {@code ;jsessionid}, ...) get the
     * documented error body instead of Spring Boot's default one.
     */
    @Bean
    public RequestRejectedHandler requestRejectedHandler(ErrorResponseWriter errorWriter) {
        return (request, response, ex) -> errorWriter.write(request, response, ErrorCode.MALFORMED_REQUEST,
                "The request URL is not allowed.");
    }

    static RequestMatcher publicEndpoints() {
        PathPatternRequestMatcher.Builder post = PathPatternRequestMatcher.withDefaults();
        List<RequestMatcher> matchers = new ArrayList<>(PUBLIC_AUTH_POSTS.stream()
                // Any method: a wrong one (GET /login) then gets 405 from MVC instead of a misleading 401.
                .map(path -> (RequestMatcher) post.matcher(path))
                .toList());
        matchers.add(post.matcher(HttpMethod.GET, "/actuator/health"));
        for (String docs : List.of("/v3/api-docs", "/v3/api-docs/**", "/swagger-ui.html", "/swagger-ui/**")) {
            matchers.add(post.matcher(HttpMethod.GET, docs));
        }
        matchers.add(post.matcher("/error"));
        return new OrRequestMatcher(matchers);
    }

    @Bean
    public CorsConfigurationSource corsConfigurationSource(CorsProperties corsProperties) {
        CorsConfiguration config = new CorsConfiguration();
        config.setAllowedOrigins(corsProperties.allowedOrigins());
        config.setAllowedMethods(List.of("GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"));
        config.setAllowedHeaders(List.of("Authorization", "Content-Type"));
        config.setMaxAge(3600L);
        UrlBasedCorsConfigurationSource source = new UrlBasedCorsConfigurationSource();
        source.registerCorsConfiguration("/api/**", config);
        return source;
    }
}
