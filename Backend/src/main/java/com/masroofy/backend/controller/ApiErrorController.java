package com.masroofy.backend.controller;

import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.ErrorResponse;
import io.swagger.v3.oas.annotations.Hidden;
import jakarta.servlet.RequestDispatcher;
import jakarta.servlet.http.HttpServletRequest;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.boot.web.servlet.error.ErrorController;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.http.ResponseEntity;
import org.springframework.transaction.CannotCreateTransactionException;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

/**
 * Replaces Spring Boot's default {@code /error} body ({@code timestamp, status, error, path}) with the documented
 * {@link ErrorResponse}, so errors raised outside MVC (servlet filters, the container) still carry a {@code code}.
 */
@Hidden
@RestController
public class ApiErrorController implements ErrorController {

    private static final Logger log = LoggerFactory.getLogger(ApiErrorController.class);

    private final Clock clock;

    public ApiErrorController(Clock clock) {
        this.clock = clock;
    }

    @RequestMapping("${server.error.path:${error.path:/error}}")
    public ResponseEntity<ErrorResponse> error(HttpServletRequest request) {
        Object statusAttribute = request.getAttribute(RequestDispatcher.ERROR_STATUS_CODE);
        int status = statusAttribute instanceof Integer value ? value : 500;
        Throwable exception = (Throwable) request.getAttribute(RequestDispatcher.ERROR_EXCEPTION);
        Object uri = request.getAttribute(RequestDispatcher.ERROR_REQUEST_URI);

        ErrorCode code = toErrorCode(status, exception);
        if (code.status().is5xxServerError()) {
            log.error("{} on {}", code, uri, exception);
        }
        ErrorResponse body = new ErrorResponse(Instant.now(clock), code.status().value(), code.name(),
                code.defaultMessage(), uri == null ? request.getRequestURI() : uri.toString(), List.of(), Map.of());
        return ResponseEntity.status(code.status()).body(body);
    }

    /** Also used by Tomcat's JSON error page ({@code JsonErrorReportValve}). */
    public static ErrorCode toErrorCode(int status, Throwable exception) {
        for (Throwable t = exception; t != null; t = t.getCause()) {
            if (t instanceof DataAccessResourceFailureException || t instanceof CannotCreateTransactionException) {
                return ErrorCode.SERVICE_UNAVAILABLE;
            }
        }
        return switch (status) {
            case 401 -> ErrorCode.UNAUTHORIZED;
            case 403 -> ErrorCode.FORBIDDEN;
            case 404 -> ErrorCode.NOT_FOUND;
            case 405 -> ErrorCode.METHOD_NOT_ALLOWED;
            case 503 -> ErrorCode.SERVICE_UNAVAILABLE;
            default -> status >= 400 && status < 500 ? ErrorCode.MALFORMED_REQUEST : ErrorCode.INTERNAL_ERROR;
        };
    }
}
