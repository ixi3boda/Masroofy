package com.masroofy.backend.firebase;

/** Tokens issued by Firebase Authentication after sign-in or refresh. */
public record FirebaseSession(String idToken, String refreshToken, long expiresInSeconds, String uid) {
}
