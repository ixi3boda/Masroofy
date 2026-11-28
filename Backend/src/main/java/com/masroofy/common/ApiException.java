package com.masroofy.common;

import org.springframework.http.HttpStatus;

/** An error with a fixed HTTP status and error_code, turned into an {@link ErrorResponse} by {@link GlobalExceptionHandler}. */
public class ApiException extends RuntimeException {

    private final HttpStatus status;
    private final String errorCode;

    public ApiException(HttpStatus status, String errorCode, String message) {
        super(message);
        this.status = status;
        this.errorCode = errorCode;
    }

    public static ApiException notFound(String message) {
        return new ApiException(HttpStatus.NOT_FOUND, "not_found", message);
    }

    public static ApiException invalidField(String message) {
        return new ApiException(HttpStatus.UNPROCESSABLE_CONTENT, "invalid_field", message);
    }

    public HttpStatus getStatus() {
        return status;
    }

    public String getErrorCode() {
        return errorCode;
    }
}
