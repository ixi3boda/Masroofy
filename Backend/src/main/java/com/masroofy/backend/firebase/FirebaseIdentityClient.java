package com.masroofy.backend.firebase;

/**
 * Everything the backend asks of Firebase Authentication. Implementations translate Firebase errors into
 * {@link com.masroofy.backend.exception.ApiException}s, so callers never see Firebase types.
 */
public interface FirebaseIdentityClient {

    /** Custom claim copied into every ID token; see {@link #setSessionVersion}. */
    String SESSION_VERSION_CLAIM = "session_version";

    /** Creates an email/password user (email not yet verified) and returns its Firebase uid. */
    String createUser(String email, String password, String displayName);

    void deleteUser(String uid);

    void markEmailVerified(String uid);

    void updatePassword(String uid, String newPassword);

    /** Invalidates every refresh token, which signs the user out on all devices. */
    void revokeRefreshTokens(String uid);

    /**
     * Stores {@code version} in the user's {@value #SESSION_VERSION_CLAIM} custom claim. ID tokens minted
     * afterwards carry it; tokens minted before keep the old value, so the backend can reject them.
     */
    void setSessionVersion(String uid, int version);

    FirebaseSession signInWithPassword(String email, String password);

    FirebaseSession refreshSession(String refreshToken);

    VerifiedToken verifyIdToken(String idToken, boolean checkRevoked);
}
