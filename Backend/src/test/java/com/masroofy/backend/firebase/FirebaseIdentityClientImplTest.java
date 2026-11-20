package com.masroofy.backend.firebase;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.content;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.header;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.method;
import static org.springframework.test.web.client.match.MockRestRequestMatchers.requestTo;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withStatus;
import static org.springframework.test.web.client.response.MockRestResponseCreators.withSuccess;

import com.google.firebase.auth.AuthErrorCode;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseAuthException;
import com.google.firebase.auth.FirebaseToken;
import com.google.firebase.auth.UserRecord;
import com.masroofy.backend.config.FirebaseProperties;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.CsvSource;
import org.springframework.http.HttpMethod;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.test.web.client.MockRestServiceServer;
import org.springframework.web.client.RestClient;

class FirebaseIdentityClientImplTest {

    private static final String SIGN_IN_URL =
            "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword";
    private static final String REFRESH_URL = "https://securetoken.googleapis.com/v1/token";

    private FirebaseAuth firebaseAuth;
    private MockRestServiceServer server;
    private FirebaseIdentityClientImpl client;

    @BeforeEach
    void setUp() {
        firebaseAuth = mock(FirebaseAuth.class);
        RestClient.Builder builder = RestClient.builder().defaultHeader("X-Goog-Api-Key", "api-key");
        server = MockRestServiceServer.bindTo(builder).build();
        FirebaseProperties properties = new FirebaseProperties(null, null, null, "api-key", true,
                "https://identitytoolkit.googleapis.com", "https://securetoken.googleapis.com");
        client = new FirebaseIdentityClientImpl(firebaseAuth, builder.build(), properties);
    }

    private static FirebaseAuthException authException(AuthErrorCode code) {
        FirebaseAuthException e = mock(FirebaseAuthException.class);
        when(e.getAuthErrorCode()).thenReturn(code);
        return e;
    }

    private static String firebaseError(String message) {
        return "{\"error\":{\"code\":400,\"message\":\"" + message + "\"}}";
    }

    // ---- REST: sign-in ----

    @Test
    void signInSendsCredentialsWithApiKeyHeaderAndParsesSession() {
        server.expect(requestTo(SIGN_IN_URL))
                .andExpect(method(HttpMethod.POST))
                .andExpect(header("X-Goog-Api-Key", "api-key"))
                .andExpect(content().json(
                        "{\"email\":\"m@example.com\",\"password\":\"pw\",\"returnSecureToken\":true}"))
                .andRespond(withSuccess("{\"idToken\":\"id\",\"refreshToken\":\"rt\",\"expiresIn\":\"3600\","
                        + "\"localId\":\"uid-1\",\"email\":\"m@example.com\",\"registered\":true}",
                        MediaType.APPLICATION_JSON));

        FirebaseSession session = client.signInWithPassword("m@example.com", "pw");

        assertThat(session).isEqualTo(new FirebaseSession("id", "rt", 3600, "uid-1"));
        server.verify();
    }

    @ParameterizedTest
    @CsvSource({
            "INVALID_LOGIN_CREDENTIALS, INVALID_CREDENTIALS",
            "EMAIL_NOT_FOUND, INVALID_CREDENTIALS",
            "INVALID_PASSWORD, INVALID_CREDENTIALS",
            "USER_DISABLED, ACCOUNT_DISABLED",
            "'TOO_MANY_ATTEMPTS_TRY_LATER : Access to this account has been temporarily disabled', RATE_LIMITED",
            "API_KEY_INVALID, AUTH_PROVIDER_UNAVAILABLE"})
    void signInErrorsAreMapped(String firebaseMessage, ErrorCode expected) {
        server.expect(requestTo(SIGN_IN_URL))
                .andRespond(withStatus(HttpStatus.BAD_REQUEST).contentType(MediaType.APPLICATION_JSON)
                        .body(firebaseError(firebaseMessage)));

        assertThatThrownBy(() -> client.signInWithPassword("m@example.com", "pw"))
                .isInstanceOfSatisfying(ApiException.class, e -> assertThat(e.getErrorCode()).isEqualTo(expected));
    }

    @Test
    void signInServerErrorIsUnavailable() {
        server.expect(requestTo(SIGN_IN_URL)).andRespond(withStatus(HttpStatus.BAD_GATEWAY).body("<html>"));

        assertThatThrownBy(() -> client.signInWithPassword("m@example.com", "pw"))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.AUTH_PROVIDER_UNAVAILABLE));
    }

    // ---- REST: refresh ----

    @Test
    void refreshPostsFormAndParsesSnakeCaseResponse() {
        server.expect(requestTo(REFRESH_URL))
                .andExpect(method(HttpMethod.POST))
                .andExpect(content().contentTypeCompatibleWith(MediaType.APPLICATION_FORM_URLENCODED))
                .andExpect(content().formDataContains(java.util.Map.of(
                        "grant_type", "refresh_token", "refresh_token", "rt")))
                .andRespond(withSuccess("{\"expires_in\":\"3600\",\"token_type\":\"Bearer\","
                        + "\"refresh_token\":\"rt2\",\"id_token\":\"id2\",\"user_id\":\"uid-1\","
                        + "\"project_id\":\"p\"}", MediaType.APPLICATION_JSON));

        assertThat(client.refreshSession("rt")).isEqualTo(new FirebaseSession("id2", "rt2", 3600, "uid-1"));
        server.verify();
    }

    @ParameterizedTest
    @CsvSource({
            "TOKEN_EXPIRED, INVALID_REFRESH_TOKEN",
            "INVALID_REFRESH_TOKEN, INVALID_REFRESH_TOKEN",
            "USER_NOT_FOUND, INVALID_REFRESH_TOKEN",
            "USER_DISABLED, ACCOUNT_DISABLED"})
    void refreshErrorsAreMapped(String firebaseMessage, ErrorCode expected) {
        server.expect(requestTo(REFRESH_URL))
                .andRespond(withStatus(HttpStatus.BAD_REQUEST).contentType(MediaType.APPLICATION_JSON)
                        .body(firebaseError(firebaseMessage)));

        assertThatThrownBy(() -> client.refreshSession("rt"))
                .isInstanceOfSatisfying(ApiException.class, e -> assertThat(e.getErrorCode()).isEqualTo(expected));
    }

    // ---- Admin SDK ----

    @Test
    void createUserReturnsUid() throws Exception {
        UserRecord record = mock(UserRecord.class);
        when(record.getUid()).thenReturn("uid-1");
        when(firebaseAuth.createUser(any(UserRecord.CreateRequest.class))).thenReturn(record);

        assertThat(client.createUser("m@example.com", "Sunny-Nile9", "Mariam")).isEqualTo("uid-1");
    }

    @Test
    void createUserWithExistingEmailIsConflict() throws Exception {
        FirebaseAuthException exists = authException(AuthErrorCode.EMAIL_ALREADY_EXISTS);
        when(firebaseAuth.createUser(any(UserRecord.CreateRequest.class))).thenThrow(exists);

        assertThatThrownBy(() -> client.createUser("m@example.com", "Sunny-Nile9", "Mariam"))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.EMAIL_ALREADY_IN_USE));
    }

    @Test
    void createUserWithInputFirebaseRejectsIsAValidationError() throws Exception {
        FirebaseAuthException invalid = mock(FirebaseAuthException.class);
        when(invalid.getErrorCode()).thenReturn(com.google.firebase.ErrorCode.INVALID_ARGUMENT);
        when(firebaseAuth.createUser(any(UserRecord.CreateRequest.class))).thenThrow(invalid);

        assertThatThrownBy(() -> client.createUser("m@example.com", "Sunny-Nile9", "Mariam"))
                .isInstanceOfSatisfying(ApiException.class, e -> {
                    assertThat(e.getErrorCode()).isEqualTo(ErrorCode.VALIDATION_FAILED);
                    assertThat(e.getFieldErrors()).extracting("field").containsExactly("email");
                });
    }

    @Test
    void verifyIdTokenReturnsClaims() throws Exception {
        FirebaseToken token = mock(FirebaseToken.class);
        when(token.getUid()).thenReturn("uid-1");
        when(token.getEmail()).thenReturn("m@example.com");
        when(firebaseAuth.verifyIdToken("t", true)).thenReturn(token);

        assertThat(client.verifyIdToken("t", true)).isEqualTo(new VerifiedToken("uid-1", "m@example.com"));
    }

    @Test
    void revokedOrExpiredTokenIsUnauthorized() throws Exception {
        FirebaseAuthException revoked = authException(AuthErrorCode.REVOKED_ID_TOKEN);
        when(firebaseAuth.verifyIdToken("t", true)).thenThrow(revoked);

        assertThatThrownBy(() -> client.verifyIdToken("t", true))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.UNAUTHORIZED));
    }

    @Test
    void disabledUserTokenIsAccountDisabled() throws Exception {
        FirebaseAuthException disabled = authException(AuthErrorCode.USER_DISABLED);
        when(firebaseAuth.verifyIdToken("t", true)).thenThrow(disabled);

        assertThatThrownBy(() -> client.verifyIdToken("t", true))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.ACCOUNT_DISABLED));
    }

    @Test
    void deletingAnAlreadyMissingUserIsFine() throws Exception {
        FirebaseAuthException missing = authException(AuthErrorCode.USER_NOT_FOUND);
        org.mockito.Mockito.doThrow(missing).when(firebaseAuth).deleteUser("uid-1");

        client.deleteUser("uid-1");
        verify(firebaseAuth).deleteUser("uid-1");
    }

    @Test
    void updatePasswordForMissingUserIsNotFound() throws Exception {
        FirebaseAuthException missing = authException(AuthErrorCode.USER_NOT_FOUND);
        when(firebaseAuth.updateUser(any(UserRecord.UpdateRequest.class))).thenThrow(missing);

        assertThatThrownBy(() -> client.updatePassword("uid-1", "Fresh-Start7"))
                .isInstanceOfSatisfying(ApiException.class,
                        e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.USER_NOT_FOUND));
    }
}
