package com.masroofy.backend.firebase;

/**
 * The claims the backend needs from a verified Firebase ID token. {@code sessionVersion} is the
 * {@value FirebaseIdentityClient#SESSION_VERSION_CLAIM} custom claim (0 when absent).
 */
public record VerifiedToken(String uid, String email, int sessionVersion) {

    public VerifiedToken(String uid, String email) {
        this(uid, email, 0);
    }
}
