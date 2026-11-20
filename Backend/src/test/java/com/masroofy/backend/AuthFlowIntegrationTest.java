package com.masroofy.backend;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.post;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.jsonPath;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.firebase.FirebaseApp;
import com.google.firebase.auth.FirebaseAuth;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.FirebaseSession;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.service.EmailService;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeEach;
import com.masroofy.backend.support.PostgresTestSupport;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.boot.test.autoconfigure.web.servlet.AutoConfigureMockMvc;
import org.springframework.boot.test.context.SpringBootTest;
import org.springframework.http.MediaType;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.security.core.userdetails.UserDetailsService;
import org.springframework.test.context.bean.override.mockito.MockitoBean;
import org.springframework.test.web.servlet.MockMvc;

/**
 * Boots the whole application (real services, JdbcTemplate repositories, Flyway schema, security) and walks
 * every auth screen in order. Only the two external systems, Firebase and SMTP, are mocked.
 */
@SpringBootTest
@AutoConfigureMockMvc
class AuthFlowIntegrationTest extends PostgresTestSupport {

    private static final String EMAIL = "mariam@example.com";

    @Autowired
    private MockMvc mvc;
    @Autowired
    private ObjectMapper json;
    @Autowired
    private JdbcTemplate jdbcTemplate;
    @Autowired
    private org.springframework.context.ApplicationContext context;

    @MockitoBean
    private FirebaseApp firebaseApp;
    @MockitoBean
    private FirebaseAuth firebaseAuth;
    @MockitoBean
    private FirebaseIdentityClient firebase;
    @MockitoBean
    private EmailService emailService;

    @BeforeEach
    @AfterEach
    void cleanDatabase() {
        // Not @Transactional (requests run in their own transactions), so clean up explicitly.
        jdbcTemplate.update("DELETE FROM auth_codes");
        jdbcTemplate.update("DELETE FROM code_dispatches");
        jdbcTemplate.update("DELETE FROM users");
    }

    private JsonNode postJson(String path, String body, int expectedStatus) throws Exception {
        String response = mvc.perform(post(path).contentType(MediaType.APPLICATION_JSON).content(body))
                .andExpect(status().is(expectedStatus))
                .andReturn().getResponse().getContentAsString();
        return json.readTree(response);
    }

    @Test
    void defaultInMemoryUserIsNotCreated() {
        assertThat(context.getBeanNamesForType(UserDetailsService.class)).isEmpty();
    }

    @Test
    void signUpVerifyLoginAndResetPassword() throws Exception {
        // 01-02 Create an account
        when(firebase.createUser(EMAIL, "Sunny-Nile9", "Mariam Ali")).thenReturn("uid-1");
        JsonNode registered = postJson("/api/v1/auth/register",
                "{\"fullName\":\"Mariam Ali\",\"email\":\"Mariam@Example.com\",\"password\":\"Sunny-Nile9\","
                        + "\"acceptedTerms\":true}", 201);
        assertThat(registered.at("/user/emailVerified").asBoolean()).isFalse();
        assertThat(registered.at("/verification/maskedEmail").asText()).isEqualTo("m***@example.com");

        ArgumentCaptor<String> code = ArgumentCaptor.forClass(String.class);
        verify(emailService).sendVerificationCode(eq(EMAIL), eq("Mariam Ali"), code.capture(), any());
        assertThat(jdbcTemplate.queryForObject("SELECT code_hash FROM auth_codes", String.class))
                .isNotEqualTo(code.getValue()).hasSize(64);

        // Duplicate sign-up
        postJson("/api/v1/auth/register", "{\"fullName\":\"Other\",\"email\":\"mariam@example.com\","
                + "\"password\":\"Sunny-Nile9\",\"acceptedTerms\":true}", 409);

        // 01-04 Log in before verifying -> told to verify
        when(firebase.signInWithPassword(EMAIL, "Sunny-Nile9"))
                .thenReturn(new FirebaseSession("id-1", "rt-1", 3600, "uid-1"));
        JsonNode notVerified = postJson("/api/v1/auth/login",
                "{\"email\":\"mariam@example.com\",\"password\":\"Sunny-Nile9\"}", 403);
        assertThat(notVerified.path("code").asText()).isEqualTo("EMAIL_NOT_VERIFIED");

        // 01-03 Resend too soon is throttled; a wrong code is counted; the right code verifies
        postJson("/api/v1/auth/email-verification/resend", "{\"email\":\"mariam@example.com\"}", 429);
        String wrong = code.getValue().equals("000000") ? "111111" : "000000";
        JsonNode wrongCode = postJson("/api/v1/auth/email-verification/verify",
                "{\"email\":\"mariam@example.com\",\"code\":\"" + wrong + "\"}", 400);
        assertThat(wrongCode.at("/details/remainingAttempts").asInt()).isEqualTo(4);
        postJson("/api/v1/auth/email-verification/verify",
                "{\"email\":\"mariam@example.com\",\"code\":\"" + code.getValue() + "\"}", 200);
        verify(firebase).markEmailVerified("uid-1");
        // A used code cannot be replayed
        postJson("/api/v1/auth/email-verification/verify",
                "{\"email\":\"mariam@example.com\",\"code\":\"" + code.getValue() + "\"}", 409);

        // 01-04 Log in, then call a protected endpoint with the token
        JsonNode tokens = postJson("/api/v1/auth/login",
                "{\"email\":\"mariam@example.com\",\"password\":\"Sunny-Nile9\"}", 200);
        assertThat(tokens.path("accessToken").asText()).isEqualTo("id-1");
        when(firebase.verifyIdToken("id-1", true)).thenReturn(new VerifiedToken("uid-1", EMAIL));
        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer id-1"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.email").value(EMAIL))
                .andExpect(jsonPath("$.emailVerified").value(true));

        // 01-05 Forgot password -> 01-06 code -> 01-07 new password
        postJson("/api/v1/auth/password/forgot", "{\"email\":\"mariam@example.com\"}", 202);
        ArgumentCaptor<String> resetCode = ArgumentCaptor.forClass(String.class);
        verify(emailService).sendPasswordResetCode(eq(EMAIL), eq("Mariam Ali"), resetCode.capture(), any());
        JsonNode resetSession = postJson("/api/v1/auth/password/verify-code",
                "{\"email\":\"mariam@example.com\",\"code\":\"" + resetCode.getValue() + "\"}", 200);
        String resetToken = resetSession.path("resetToken").asText();
        assertThat(resetToken).isNotBlank();

        when(firebase.signInWithPassword(EMAIL, "Sunny-Nile9"))
                .thenReturn(new FirebaseSession("id-x", "rt-x", 3600, "uid-1"));
        JsonNode reused = postJson("/api/v1/auth/password/reset", "{\"resetToken\":\"" + resetToken
                + "\",\"newPassword\":\"Sunny-Nile9\",\"confirmPassword\":\"Sunny-Nile9\"}", 400);
        assertThat(reused.path("code").asText()).isEqualTo("PASSWORD_REUSED");

        when(firebase.signInWithPassword(EMAIL, "Fresh-Start7"))
                .thenThrow(new ApiException(ErrorCode.INVALID_CREDENTIALS));
        postJson("/api/v1/auth/password/reset", "{\"resetToken\":\"" + resetToken
                + "\",\"newPassword\":\"Fresh-Start7\",\"confirmPassword\":\"Fresh-Start7\"}", 200);
        verify(firebase).updatePassword("uid-1", "Fresh-Start7");
        verify(firebase).setSessionVersion("uid-1", 1);
        verify(firebase).revokeRefreshTokens("uid-1");

        // The access token from before the reset no longer works, even though Firebase still accepts it
        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer id-1"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));

        // The reset token works only once
        JsonNode replay = postJson("/api/v1/auth/password/reset", "{\"resetToken\":\"" + resetToken
                + "\",\"newPassword\":\"Fresh-Start8\",\"confirmPassword\":\"Fresh-Start8\"}", 400);
        assertThat(replay.path("code").asText()).isEqualTo("INVALID_RESET_TOKEN");

        // A token minted after the reset carries session_version 1 and works
        when(firebase.verifyIdToken("id-2", true)).thenReturn(new VerifiedToken("uid-1", EMAIL, 1));
        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer id-2"))
                .andExpect(status().isOk());

        // Logout ends it immediately
        mvc.perform(post("/api/v1/auth/logout").header("Authorization", "Bearer id-2"))
                .andExpect(status().isNoContent());
        verify(firebase).setSessionVersion("uid-1", 2);
        verify(firebase, org.mockito.Mockito.times(2)).revokeRefreshTokens("uid-1");
        mvc.perform(get("/api/v1/users/me").header("Authorization", "Bearer id-2"))
                .andExpect(status().isUnauthorized());
    }

    @Test
    void urlsRejectedByTheFirewallGetTheDocumentedErrorBody() throws Exception {
        // MockMvc normalizes "//" before the firewall sees it, so call the registered handler directly;
        // the hard test (SEC-10..15) checks the wiring with raw URLs against the running server.
        var handler = context.getBean(org.springframework.security.web.firewall.RequestRejectedHandler.class);
        var request = new org.springframework.mock.web.MockHttpServletRequest("GET", "/api/v1//users/me");
        var response = new org.springframework.mock.web.MockHttpServletResponse();

        handler.handle(request, response, new org.springframework.security.web.firewall.RequestRejectedException("//"));

        JsonNode body = json.readTree(response.getContentAsString());
        assertThat(response.getStatus()).isEqualTo(400);
        assertThat(body.path("code").asText()).isEqualTo("MALFORMED_REQUEST");
        assertThat(body.path("path").asText()).isEqualTo("/api/v1//users/me");
    }

    @Test
    void secondResendAnswersTheSameForKnownAndUnknownEmails() throws Exception {
        when(firebase.createUser(anyString(), anyString(), anyString())).thenReturn("uid-1");
        postJson("/api/v1/auth/register", "{\"fullName\":\"Mariam Ali\",\"email\":\"mariam@example.com\","
                + "\"password\":\"Sunny-Nile9\",\"acceptedTerms\":true}", 201);

        // Sign-up started the cooldown for the real email; an unknown email gets it on its first call.
        postJson("/api/v1/auth/email-verification/resend", "{\"email\":\"mariam@example.com\"}", 429);
        postJson("/api/v1/auth/email-verification/resend", "{\"email\":\"nobody@example.com\"}", 202);
        JsonNode unknown = postJson("/api/v1/auth/email-verification/resend", "{\"email\":\"nobody@example.com\"}", 429);
        assertThat(unknown.path("code").asText()).isEqualTo("RESEND_COOLDOWN");

        postJson("/api/v1/auth/password/forgot", "{\"email\":\"mariam@example.com\"}", 202);
        postJson("/api/v1/auth/password/forgot", "{\"email\":\"nobody@example.com\"}", 202);
        JsonNode known = postJson("/api/v1/auth/password/forgot", "{\"email\":\"mariam@example.com\"}", 429);
        JsonNode stranger = postJson("/api/v1/auth/password/forgot", "{\"email\":\"nobody@example.com\"}", 429);
        assertThat(known.path("code").asText()).isEqualTo(stranger.path("code").asText()).isEqualTo("RESEND_COOLDOWN");
        assertThat(jdbcTemplate.queryForObject("SELECT count(*) FROM code_dispatches WHERE email_hash LIKE '%@%'",
                Integer.class)).isZero();
    }

    @Test
    void swaggerUiAndOpenApiDocsArePublic() throws Exception {
        String docs = mvc.perform(get("/v3/api-docs"))
                .andExpect(status().isOk())
                .andExpect(jsonPath("$.info.title").value("Masroofy API"))
                .andExpect(jsonPath("$.components.securitySchemes.bearerAuth.scheme").value("bearer"))
                .andReturn().getResponse().getContentAsString();
        JsonNode paths = json.readTree(docs).path("paths");
        for (String path : new String[] {"/api/v1/auth/register", "/api/v1/auth/login", "/api/v1/auth/token/refresh",
                "/api/v1/auth/logout", "/api/v1/auth/email-verification/verify",
                "/api/v1/auth/email-verification/resend", "/api/v1/auth/password/forgot",
                "/api/v1/auth/password/verify-code", "/api/v1/auth/password/reset", "/api/v1/users/me"}) {
            assertThat(paths.has(path)).as(path).isTrue();
        }
        assertThat(paths.at("/~1api~1v1~1users~1me/get/security/0").has("bearerAuth")).isTrue();
        mvc.perform(get("/swagger-ui/index.html")).andExpect(status().isOk());
    }

    @Test
    void unknownRouteReturnsJsonErrorNotHtml() throws Exception {
        when(firebase.verifyIdToken(anyString(), eq(true))).thenThrow(new ApiException(ErrorCode.UNAUTHORIZED));
        mvc.perform(get("/api/v1/nope"))
                .andExpect(status().isUnauthorized())
                .andExpect(jsonPath("$.code").value("UNAUTHORIZED"));
    }
}
