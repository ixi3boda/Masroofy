package com.masroofy.backend.dto.response;

/** Account created; the app moves to "Verify signup email" (01-03). */
public record RegisterResponse(
        UserResponse user,
        CodeDispatchResponse verification,
        boolean verificationEmailSent) {
}
