package com.masroofy.backend.firebase;

/** The claims the backend needs from a verified Firebase ID token. */
public record VerifiedToken(String uid, String email) {
}
