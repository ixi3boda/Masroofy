package com.masroofy.backend.dto.response;

/**
 * Login / refresh result. Send {@code accessToken} as {@code Authorization: Bearer <accessToken>};
 * when it expires (after {@code expiresIn} seconds) call the refresh endpoint with {@code refreshToken}.
 */
public record AuthTokensResponse(
        String accessToken,
        String refreshToken,
        String tokenType,
        long expiresIn,
        UserResponse user) {

    public static final String BEARER = "Bearer";

    @Override
    public String toString() {
        return "AuthTokensResponse[accessToken=***, refreshToken=***, expiresIn=" + expiresIn + "]";
    }
}
