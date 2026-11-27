package com.masroofy.backend.service;

import java.util.UUID;

/** Published after a sign-up has been saved (the user exists in Firebase and PostgreSQL). */
public record UserRegisteredEvent(UUID userId, String email) {
}
