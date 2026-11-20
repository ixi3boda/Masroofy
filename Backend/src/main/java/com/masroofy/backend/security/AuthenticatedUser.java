package com.masroofy.backend.security;

import java.util.UUID;

/** The principal placed in the SecurityContext for a request carrying a valid Firebase ID token. */
public record AuthenticatedUser(UUID userId, String firebaseUid, String email, boolean emailVerified) {
}
