package com.masroofy.backend.firebase;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;
import com.fasterxml.jackson.annotation.JsonProperty;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.google.firebase.auth.AuthErrorCode;
import com.google.firebase.auth.FirebaseAuth;
import com.google.firebase.auth.FirebaseAuthException;
import com.google.firebase.auth.FirebaseToken;
import com.google.firebase.auth.UserRecord;
import com.masroofy.backend.config.FirebaseProperties;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import java.io.IOException;
import java.io.InputStream;
import java.net.URI;
import java.util.Map;
import java.util.Set;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClient;

@Component
public class FirebaseIdentityClientImpl implements FirebaseIdentityClient {

    private static final Logger log = LoggerFactory.getLogger(FirebaseIdentityClientImpl.class);

    private static final Set<String> BAD_CREDENTIAL_ERRORS =
            Set.of("INVALID_LOGIN_CREDENTIALS", "EMAIL_NOT_FOUND", "INVALID_PASSWORD", "INVALID_EMAIL");
    private static final Set<String> BAD_REFRESH_ERRORS = Set.of("TOKEN_EXPIRED", "INVALID_REFRESH_TOKEN",
            "USER_NOT_FOUND", "INVALID_GRANT_TYPE", "MISSING_REFRESH_TOKEN");

    private final FirebaseAuth firebaseAuth;
    private final RestClient restClient;
    private final FirebaseProperties properties;
    private final ObjectMapper objectMapper = new ObjectMapper();

    public FirebaseIdentityClientImpl(FirebaseAuth firebaseAuth, RestClient firebaseRestClient,
                                      FirebaseProperties properties) {
        this.firebaseAuth = firebaseAuth;
        this.restClient = firebaseRestClient;
        this.properties = properties;
    }

    // ---- Admin SDK --------------------------------------------------------------------------------------

    @Override
    public String createUser(String email, String password, String displayName) {
        UserRecord.CreateRequest request;
        try {
            request = new UserRecord.CreateRequest()
                    .setEmail(email)
                    .setPassword(password)
                    .setDisplayName(displayName)
                    .setEmailVerified(false)
                    .setDisabled(false);
        } catch (IllegalArgumentException e) {
            throw invalidEmail();
        }
        try {
            return firebaseAuth.createUser(request).getUid();
        } catch (FirebaseAuthException e) {
            if (e.getAuthErrorCode() == AuthErrorCode.EMAIL_ALREADY_EXISTS) {
                throw new ApiException(ErrorCode.EMAIL_ALREADY_IN_USE);
            }
            if (e.getErrorCode() == com.google.firebase.ErrorCode.INVALID_ARGUMENT) {
                // Firebase refused the input itself (e.g. an email format it does not accept): a client error.
                log.warn("Firebase rejected sign-up input: {}", e.getMessage());
                throw invalidEmail();
            }
            throw unavailable("createUser", e);
        }
    }

    @Override
    public void deleteUser(String uid) {
        try {
            firebaseAuth.deleteUser(uid);
        } catch (FirebaseAuthException e) {
            if (e.getAuthErrorCode() != AuthErrorCode.USER_NOT_FOUND) {
                throw unavailable("deleteUser", e);
            }
        }
    }

    @Override
    public void markEmailVerified(String uid) {
        updateUser(new UserRecord.UpdateRequest(uid).setEmailVerified(true), "markEmailVerified");
    }

    @Override
    public void updatePassword(String uid, String newPassword) {
        updateUser(new UserRecord.UpdateRequest(uid).setPassword(newPassword), "updatePassword");
    }

    @Override
    public void revokeRefreshTokens(String uid) {
        try {
            firebaseAuth.revokeRefreshTokens(uid);
        } catch (FirebaseAuthException e) {
            if (e.getAuthErrorCode() != AuthErrorCode.USER_NOT_FOUND) {
                throw unavailable("revokeRefreshTokens", e);
            }
        }
    }

    @Override
    public VerifiedToken verifyIdToken(String idToken, boolean checkRevoked) {
        try {
            FirebaseToken token = firebaseAuth.verifyIdToken(idToken, checkRevoked);
            return new VerifiedToken(token.getUid(), token.getEmail());
        } catch (FirebaseAuthException e) {
            AuthErrorCode code = e.getAuthErrorCode();
            if (code == AuthErrorCode.USER_DISABLED) {
                throw new ApiException(ErrorCode.ACCOUNT_DISABLED);
            }
            if (code == AuthErrorCode.CERTIFICATE_FETCH_FAILED) {
                throw unavailable("verifyIdToken", e);
            }
            throw new ApiException(ErrorCode.UNAUTHORIZED, "The access token is invalid or has expired.");
        } catch (IllegalArgumentException e) {
            throw new ApiException(ErrorCode.UNAUTHORIZED, "The access token is invalid or has expired.");
        }
    }

    private void updateUser(UserRecord.UpdateRequest request, String operation) {
        try {
            firebaseAuth.updateUser(request);
        } catch (FirebaseAuthException e) {
            if (e.getAuthErrorCode() == AuthErrorCode.USER_NOT_FOUND) {
                throw new ApiException(ErrorCode.USER_NOT_FOUND);
            }
            throw unavailable(operation, e);
        }
    }

    // ---- REST API (password sign-in and token refresh are not part of the Admin SDK) ----------------------

    @Override
    public FirebaseSession signInWithPassword(String email, String password) {
        URI uri = URI.create(properties.identityToolkitBaseUrl() + "/v1/accounts:signInWithPassword");
        SignInResponse response = call(() -> restClient.post()
                .uri(uri)
                .contentType(MediaType.APPLICATION_JSON)
                .body(Map.of("email", email, "password", password, "returnSecureToken", true))
                .retrieve()
                .onStatus(HttpStatusCode::isError, (req, res) -> {
                    throw mapSignInError(res.getStatusCode(), readErrorMessage(res.getBody()));
                })
                .body(SignInResponse.class));
        if (response == null || response.idToken() == null) {
            throw new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE);
        }
        return new FirebaseSession(response.idToken(), response.refreshToken(),
                parseSeconds(response.expiresIn()), response.localId());
    }

    @Override
    public FirebaseSession refreshSession(String refreshToken) {
        URI uri = URI.create(properties.secureTokenBaseUrl() + "/v1/token");
        MultiValueMap<String, String> form = new LinkedMultiValueMap<>();
        form.add("grant_type", "refresh_token");
        form.add("refresh_token", refreshToken);
        RefreshResponse response = call(() -> restClient.post()
                .uri(uri)
                .contentType(MediaType.APPLICATION_FORM_URLENCODED)
                .body(form)
                .retrieve()
                .onStatus(HttpStatusCode::isError, (req, res) -> {
                    throw mapRefreshError(res.getStatusCode(), readErrorMessage(res.getBody()));
                })
                .body(RefreshResponse.class));
        if (response == null || response.idToken() == null) {
            throw new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE);
        }
        return new FirebaseSession(response.idToken(), response.refreshToken(),
                parseSeconds(response.expiresIn()), response.userId());
    }

    static ApiException mapSignInError(HttpStatusCode status, String firebaseError) {
        if (BAD_CREDENTIAL_ERRORS.contains(firebaseError)) {
            return new ApiException(ErrorCode.INVALID_CREDENTIALS);
        }
        if ("USER_DISABLED".equals(firebaseError)) {
            return new ApiException(ErrorCode.ACCOUNT_DISABLED);
        }
        if ("TOO_MANY_ATTEMPTS_TRY_LATER".equals(firebaseError)) {
            return new ApiException(ErrorCode.RATE_LIMITED);
        }
        log.error("Firebase sign-in failed with HTTP {} and error {}", status.value(), firebaseError);
        return new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE);
    }

    static ApiException mapRefreshError(HttpStatusCode status, String firebaseError) {
        if (BAD_REFRESH_ERRORS.contains(firebaseError)) {
            return new ApiException(ErrorCode.INVALID_REFRESH_TOKEN);
        }
        if ("USER_DISABLED".equals(firebaseError)) {
            return new ApiException(ErrorCode.ACCOUNT_DISABLED);
        }
        log.error("Firebase token refresh failed with HTTP {} and error {}", status.value(), firebaseError);
        return new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE);
    }

    /** Firebase error messages look like {@code "TOO_MANY_ATTEMPTS_TRY_LATER : details"}; keep the code. */
    String readErrorMessage(InputStream body) {
        try {
            JsonNode message = objectMapper.readTree(body).path("error").path("message");
            if (message.isMissingNode() || message.isNull()) {
                return "";
            }
            String text = message.asText().trim();
            int separator = text.indexOf(' ');
            return separator > 0 ? text.substring(0, separator) : text;
        } catch (IOException e) {
            return "";
        }
    }

    private static long parseSeconds(String value) {
        try {
            return Long.parseLong(value);
        } catch (NumberFormatException e) {
            return 3600L;
        }
    }

    private static <T> T call(java.util.function.Supplier<T> request) {
        try {
            return request.get();
        } catch (ResourceAccessException e) {
            log.error("Firebase Auth REST API unreachable", e);
            throw new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE, e);
        }
    }

    private static ApiException invalidEmail() {
        String message = "Enter a valid email address";
        return new ApiException(ErrorCode.VALIDATION_FAILED, ErrorCode.VALIDATION_FAILED.defaultMessage(),
                java.util.Map.of(), java.util.List.of(
                        new com.masroofy.backend.exception.FieldErrorDetail("email", "Email", message)), null);
    }

    private static ApiException unavailable(String operation, FirebaseAuthException e) {
        log.error("Firebase {} failed: {} / {}", operation, e.getErrorCode(), e.getAuthErrorCode(), e);
        return new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE, e);
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    record SignInResponse(String idToken, String refreshToken, String expiresIn, String localId) {
    }

    @JsonIgnoreProperties(ignoreUnknown = true)
    record RefreshResponse(@JsonProperty("id_token") String idToken,
                           @JsonProperty("refresh_token") String refreshToken,
                           @JsonProperty("expires_in") String expiresIn,
                           @JsonProperty("user_id") String userId) {
    }
}
