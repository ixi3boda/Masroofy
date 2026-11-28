package com.masroofy.common;

import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.MissingServletRequestParameterException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.client.HttpStatusCodeException;
import org.springframework.web.client.ResourceAccessException;
import org.springframework.web.client.RestClientException;
import org.springframework.web.method.annotation.MethodArgumentTypeMismatchException;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.multipart.support.MissingServletRequestPartException;
import org.springframework.web.servlet.resource.NoResourceFoundException;
import tools.jackson.databind.JsonNode;
import tools.jackson.databind.json.JsonMapper;

import java.util.stream.Collectors;

/**
 * Turns every error into {"error_code": "...", "message": "..."} so the app handles them all the same way.
 *
 * It is a global @RestControllerAdvice (not a handler inside a controller) because some errors,
 * such as an upload over 10 MB, happen before any controller runs.
 */
@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);
    private static final JsonMapper JSON = JsonMapper.builder().build();

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ErrorResponse> api(ApiException e) {
        return error(e.getStatus(), e.getErrorCode(), e.getMessage());
    }

    // ---------------- Python voice service ----------------

    /** The voice service answered with an error (400/413/415/422...): keep its status code and message. */
    @ExceptionHandler(HttpStatusCodeException.class)
    public ResponseEntity<?> voiceServiceError(HttpStatusCodeException e) {
        String body = e.getResponseBodyAsString();
        try {
            JsonNode json = JSON.readTree(body);
            if (json.has("error_code")) {
                return ResponseEntity.status(e.getStatusCode()).body(json);
            }
        } catch (RuntimeException notJson) {
            // fall through
        }
        return ResponseEntity.status(e.getStatusCode())
                .body(new ErrorResponse("voice_service_error", body.isBlank() ? e.getMessage() : body));
    }

    @ExceptionHandler(ResourceAccessException.class)
    public ResponseEntity<ErrorResponse> voiceServiceUnavailable(ResourceAccessException e) {
        return error(HttpStatus.SERVICE_UNAVAILABLE, "voice_service_unavailable",
                "The voice service is not running or did not answer in time. Start it with: "
                        + "uvicorn voice_expense.api:app --host 127.0.0.1 --port 8000");
    }

    @ExceptionHandler(RestClientException.class)
    public ResponseEntity<ErrorResponse> voiceServiceBroken(RestClientException e) {
        log.warn("Voice service call failed", e);
        return error(HttpStatus.BAD_GATEWAY, "voice_service_error", e.getMessage());
    }

    // ---------------- Bad requests ----------------

    @ExceptionHandler(MaxUploadSizeExceededException.class)
    public ResponseEntity<ErrorResponse> tooLarge(MaxUploadSizeExceededException e) {
        return error(HttpStatus.CONTENT_TOO_LARGE, "file_too_large", "The recording is larger than 10 MB.");
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> invalidBody(MethodArgumentNotValidException e) {
        String message = e.getBindingResult().getFieldErrors().stream()
                .map(f -> snakeCase(f.getField()) + ": " + f.getDefaultMessage())
                .sorted()
                .collect(Collectors.joining("; "));
        return error(HttpStatus.UNPROCESSABLE_CONTENT, "validation_error", message);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> unreadable(HttpMessageNotReadableException e) {
        return error(HttpStatus.BAD_REQUEST, "invalid_json",
                "The request body is not valid JSON or has a value of the wrong type (dates are YYYY-MM-DD, times HH:MM).");
    }

    @ExceptionHandler({MissingServletRequestParameterException.class, MissingServletRequestPartException.class})
    public ResponseEntity<ErrorResponse> missingParameter(Exception e) {
        return error(HttpStatus.BAD_REQUEST, "missing_parameter", e.getMessage());
    }

    @ExceptionHandler(MethodArgumentTypeMismatchException.class)
    public ResponseEntity<ErrorResponse> badParameter(MethodArgumentTypeMismatchException e) {
        return error(HttpStatus.BAD_REQUEST, "invalid_parameter",
                "Invalid value '" + e.getValue() + "' for parameter '" + e.getName() + "'");
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ErrorResponse> noSuchUrl(NoResourceFoundException e) {
        return error(HttpStatus.NOT_FOUND, "not_found", "No endpoint " + e.getHttpMethod() + " /" + e.getResourcePath());
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ErrorResponse> wrongMethod(HttpRequestMethodNotSupportedException e) {
        return error(HttpStatus.METHOD_NOT_ALLOWED, "method_not_allowed", e.getMessage());
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<ErrorResponse> wrongContentType(HttpMediaTypeNotSupportedException e) {
        return error(HttpStatus.UNSUPPORTED_MEDIA_TYPE, "unsupported_media_type", e.getMessage());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> unexpected(Exception e) {
        log.error("Unexpected error", e);
        return error(HttpStatus.INTERNAL_SERVER_ERROR, "internal_error", e.getClass().getSimpleName() + ": " + e.getMessage());
    }

    private static ResponseEntity<ErrorResponse> error(HttpStatus status, String code, String message) {
        return ResponseEntity.status(status).body(new ErrorResponse(code, message));
    }

    private static String snakeCase(String field) {
        return field.replaceAll("([a-z0-9])([A-Z])", "$1_$2").toLowerCase();
    }
}
