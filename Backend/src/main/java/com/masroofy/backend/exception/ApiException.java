package com.masroofy.backend.exception;

import java.util.Collections;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/** Base exception for every error that is returned to the client with a known {@link ErrorCode}. */
public class ApiException extends RuntimeException {

    private final ErrorCode errorCode;
    private final transient Map<String, Object> details;
    private final transient List<FieldErrorDetail> fieldErrors;

    public ApiException(ErrorCode errorCode) {
        this(errorCode, errorCode.defaultMessage(), Map.of(), List.of(), null);
    }

    public ApiException(ErrorCode errorCode, String message) {
        this(errorCode, message, Map.of(), List.of(), null);
    }

    public ApiException(ErrorCode errorCode, Map<String, Object> details) {
        this(errorCode, errorCode.defaultMessage(), details, List.of(), null);
    }

    public ApiException(ErrorCode errorCode, Throwable cause) {
        this(errorCode, errorCode.defaultMessage(), Map.of(), List.of(), cause);
    }

    public ApiException(ErrorCode errorCode, String message, Map<String, Object> details,
                        List<FieldErrorDetail> fieldErrors, Throwable cause) {
        super(message, cause);
        this.errorCode = errorCode;
        this.details = Collections.unmodifiableMap(new LinkedHashMap<>(details));
        this.fieldErrors = List.copyOf(fieldErrors);
    }

    public ErrorCode getErrorCode() {
        return errorCode;
    }

    public Map<String, Object> getDetails() {
        return details;
    }

    public List<FieldErrorDetail> getFieldErrors() {
        return fieldErrors;
    }
}
