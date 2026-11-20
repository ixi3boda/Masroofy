package com.masroofy.backend.exception;

import org.springframework.http.HttpStatus;

/** Stable, machine-readable error codes. The Android app switches on {@link #name()}. */
public enum ErrorCode {
    VALIDATION_FAILED(HttpStatus.BAD_REQUEST, "Some fields are invalid."),
    MALFORMED_REQUEST(HttpStatus.BAD_REQUEST, "The request body is missing or malformed."),
    WEAK_PASSWORD(HttpStatus.BAD_REQUEST, "The password does not meet the requirements."),
    PASSWORDS_DO_NOT_MATCH(HttpStatus.BAD_REQUEST, "Both passwords must match."),
    PASSWORD_REUSED(HttpStatus.BAD_REQUEST, "Use a password you have not used for this account before."),
    INVALID_CODE(HttpStatus.BAD_REQUEST, "The code is incorrect."),
    INVALID_OR_EXPIRED_CODE(HttpStatus.BAD_REQUEST, "The code is invalid or has expired. Request a new code."),
    INVALID_RESET_TOKEN(HttpStatus.BAD_REQUEST, "The password reset session is invalid or has expired. Start again."),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "Incorrect email or password."),
    INVALID_REFRESH_TOKEN(HttpStatus.UNAUTHORIZED, "Your session has expired. Log in again."),
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "Authentication is required."),
    EMAIL_NOT_VERIFIED(HttpStatus.FORBIDDEN, "Verify your email before logging in."),
    ACCOUNT_DISABLED(HttpStatus.FORBIDDEN, "This account has been disabled."),
    FORBIDDEN(HttpStatus.FORBIDDEN, "You do not have access to this resource."),
    NOT_FOUND(HttpStatus.NOT_FOUND, "The resource was not found."),
    USER_NOT_FOUND(HttpStatus.NOT_FOUND, "The user was not found."),
    METHOD_NOT_ALLOWED(HttpStatus.METHOD_NOT_ALLOWED, "This method is not allowed."),
    EMAIL_ALREADY_IN_USE(HttpStatus.CONFLICT, "An account with this email already exists."),
    EMAIL_ALREADY_VERIFIED(HttpStatus.CONFLICT, "This email is already verified. You can log in."),
    TOO_MANY_ATTEMPTS(HttpStatus.TOO_MANY_REQUESTS, "Too many incorrect attempts. Request a new code."),
    RESEND_COOLDOWN(HttpStatus.TOO_MANY_REQUESTS, "Please wait before requesting another code."),
    RATE_LIMITED(HttpStatus.TOO_MANY_REQUESTS, "Too many requests. Try again later."),
    INTERNAL_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "Something went wrong. Try again later."),
    EMAIL_DELIVERY_FAILED(HttpStatus.SERVICE_UNAVAILABLE, "We could not send the email. Try again later."),
    AUTH_PROVIDER_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "Authentication is temporarily unavailable. Try again later."),
    /** The database cannot be reached. Safe to retry later. */
    SERVICE_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "The service is temporarily unavailable. Try again later.");

    private final HttpStatus status;
    private final String defaultMessage;

    ErrorCode(HttpStatus status, String defaultMessage) {
        this.status = status;
        this.defaultMessage = defaultMessage;
    }

    public HttpStatus status() {
        return status;
    }

    public String defaultMessage() {
        return defaultMessage;
    }
}
