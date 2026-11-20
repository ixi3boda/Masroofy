package com.masroofy.backend.dto.response;

/** The reset code was accepted; pass {@code resetToken} to the reset endpoint within the expiry. */
public record ResetCodeVerifiedResponse(String resetToken, long expiresInSeconds) {

    @Override
    public String toString() {
        return "ResetCodeVerifiedResponse[resetToken=***, expiresInSeconds=" + expiresInSeconds + "]";
    }
}
