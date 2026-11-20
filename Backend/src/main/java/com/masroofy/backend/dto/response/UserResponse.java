package com.masroofy.backend.dto.response;

import com.masroofy.backend.model.User;
import java.time.Instant;
import java.util.UUID;

/** Public view of a USER. Never exposes the Firebase uid or FCM token. */
public record UserResponse(
        UUID id,
        String fullName,
        String email,
        String phone,
        String baseCurrency,
        String locale,
        String timezone,
        boolean emailVerified,
        Instant emailVerifiedAt,
        Instant createdAt) {

    public static UserResponse from(User user) {
        return new UserResponse(user.id(), user.fullName(), user.email(), user.phone(), user.baseCurrency(),
                user.locale(), user.timezone(), user.isEmailVerified(), user.emailVerifiedAt(), user.createdAt());
    }
}
