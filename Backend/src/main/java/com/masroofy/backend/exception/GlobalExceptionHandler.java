package com.masroofy.backend.exception;

import jakarta.servlet.http.HttpServletRequest;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.http.ResponseEntity;
import org.springframework.http.converter.HttpMessageNotReadableException;
import org.springframework.validation.FieldError;
import org.springframework.web.HttpMediaTypeNotSupportedException;
import org.springframework.web.HttpRequestMethodNotSupportedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.servlet.resource.NoResourceFoundException;

@RestControllerAdvice
public class GlobalExceptionHandler {

    private static final Logger log = LoggerFactory.getLogger(GlobalExceptionHandler.class);

    private final Clock clock;

    public GlobalExceptionHandler(Clock clock) {
        this.clock = clock;
    }

    @ExceptionHandler(ApiException.class)
    public ResponseEntity<ErrorResponse> handleApi(ApiException ex, HttpServletRequest request) {
        if (ex.getErrorCode().status().is5xxServerError()) {
            log.error("{} on {}: {}", ex.getErrorCode(), request.getRequestURI(), ex.getMessage(), ex);
        }
        ResponseEntity.BodyBuilder builder = ResponseEntity.status(ex.getErrorCode().status());
        Object retryAfter = ex.getDetails().get("retryAfterSeconds");
        if (retryAfter != null) {
            builder.header("Retry-After", retryAfter.toString());
        }
        return builder.body(body(ex.getErrorCode(), ex.getMessage(), request, ex.getFieldErrors(), ex.getDetails()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex,
                                                          HttpServletRequest request) {
        List<FieldErrorDetail> fieldErrors = ex.getBindingResult().getFieldErrors().stream()
                .map(GlobalExceptionHandler::toDetail)
                .toList();
        return respond(ErrorCode.VALIDATION_FAILED, request, fieldErrors);
    }

    @ExceptionHandler(HttpMessageNotReadableException.class)
    public ResponseEntity<ErrorResponse> handleUnreadable(HttpMessageNotReadableException ex,
                                                          HttpServletRequest request) {
        return respond(ErrorCode.MALFORMED_REQUEST, request, List.of());
    }

    @ExceptionHandler(HttpMediaTypeNotSupportedException.class)
    public ResponseEntity<ErrorResponse> handleMediaType(HttpMediaTypeNotSupportedException ex,
                                                         HttpServletRequest request) {
        return respond(ErrorCode.MALFORMED_REQUEST, request, List.of());
    }

    @ExceptionHandler(HttpRequestMethodNotSupportedException.class)
    public ResponseEntity<ErrorResponse> handleMethod(HttpRequestMethodNotSupportedException ex,
                                                      HttpServletRequest request) {
        return respond(ErrorCode.METHOD_NOT_ALLOWED, request, List.of());
    }

    @ExceptionHandler(NoResourceFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(NoResourceFoundException ex, HttpServletRequest request) {
        return respond(ErrorCode.NOT_FOUND, request, List.of());
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleUnexpected(Exception ex, HttpServletRequest request) {
        log.error("Unhandled error on {}", request.getRequestURI(), ex);
        return respond(ErrorCode.INTERNAL_ERROR, request, List.of());
    }

    private ResponseEntity<ErrorResponse> respond(ErrorCode code, HttpServletRequest request,
                                                  List<FieldErrorDetail> fieldErrors) {
        return ResponseEntity.status(code.status())
                .body(body(code, code.defaultMessage(), request, fieldErrors, Map.of()));
    }

    private ErrorResponse body(ErrorCode code, String message, HttpServletRequest request,
                               List<FieldErrorDetail> fieldErrors, Map<String, Object> details) {
        return new ErrorResponse(Instant.now(clock), code.status().value(), code.name(), message,
                request.getRequestURI(), fieldErrors, details);
    }

    private static FieldErrorDetail toDetail(FieldError error) {
        return new FieldErrorDetail(error.getField(), error.getCode(), error.getDefaultMessage());
    }
}
