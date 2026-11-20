package com.masroofy.backend.firebase;

/**
 * Everything the backend asks of Firebase Authentication. Implementations translate Firebase errors into
 * {@link com.masroofy.backend.exception.ApiException}s, so callers never see Firebase types.
 */
public interface FirebaseIdentityClient {

    /** Creates an email/password user (email not yet verified) and returns its Firebase uid. */
    String createUser(String email, String password, String displayName);

    void deleteUser(String uid);

    void markEmailVerified(String uid);

    void updatePassword(String uid, String newPassword);

    /** Invalidates every refresh token, which signs the user out on all devices. */
    void revokeRefreshTokens(String uid);

    FirebaseSession signInWithPassword(String email, String password);

    FirebaseSession refreshSession(String refreshToken);

    VerifiedToken verifyIdToken(String idToken, boolean checkRevoked);
}
