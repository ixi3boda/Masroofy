package com.masroofy.backend.controller;

import static org.assertj.core.api.Assertions.assertThat;

import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.ErrorResponse;
import jakarta.servlet.RequestDispatcher;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import org.junit.jupiter.api.Test;
import org.springframework.jdbc.CannotGetJdbcConnectionException;
import org.springframework.mock.web.MockHttpServletRequest;
import org.springframework.transaction.CannotCreateTransactionException;

class ApiErrorControllerTest {

    private final ApiErrorController controller =
            new ApiErrorController(Clock.fixed(Instant.parse("2026-11-20T10:00:00Z"), ZoneOffset.UTC));

    @Test
    void mapsServletErrorStatusesToDocumentedCodes() {
        assertThat(ApiErrorController.toErrorCode(400, null)).isEqualTo(ErrorCode.MALFORMED_REQUEST);
        assertThat(ApiErrorController.toErrorCode(401, null)).isEqualTo(ErrorCode.UNAUTHORIZED);
        assertThat(ApiErrorController.toErrorCode(403, null)).isEqualTo(ErrorCode.FORBIDDEN);
        assertThat(ApiErrorController.toErrorCode(404, null)).isEqualTo(ErrorCode.NOT_FOUND);
        assertThat(ApiErrorController.toErrorCode(405, null)).isEqualTo(ErrorCode.METHOD_NOT_ALLOWED);
        assertThat(ApiErrorController.toErrorCode(413, null)).isEqualTo(ErrorCode.MALFORMED_REQUEST);
        assertThat(ApiErrorController.toErrorCode(500, null)).isEqualTo(ErrorCode.INTERNAL_ERROR);
        assertThat(ApiErrorController.toErrorCode(503, null)).isEqualTo(ErrorCode.SERVICE_UNAVAILABLE);
    }

    @Test
    void databaseOutagesAre503WhateverTheStatusSays() {
        assertThat(ApiErrorController.toErrorCode(500, new RuntimeException(new CannotGetJdbcConnectionException("x"))))
                .isEqualTo(ErrorCode.SERVICE_UNAVAILABLE);
        assertThat(ApiErrorController.toErrorCode(500, new CannotCreateTransactionException("x")))
                .isEqualTo(ErrorCode.SERVICE_UNAVAILABLE);
    }

    @Test
    void writesTheDocumentedBodyForTheOriginalPath() {
        MockHttpServletRequest request = new MockHttpServletRequest("GET", "/error");
        request.setAttribute(RequestDispatcher.ERROR_STATUS_CODE, 404);
        request.setAttribute(RequestDispatcher.ERROR_REQUEST_URI, "/api/v1/nope");

        var response = controller.error(request);

        ErrorResponse body = response.getBody();
        assertThat(response.getStatusCode().value()).isEqualTo(404);
        assertThat(body.code()).isEqualTo("NOT_FOUND");
        assertThat(body.path()).isEqualTo("/api/v1/nope");
        assertThat(body.timestamp()).isEqualTo(Instant.parse("2026-11-20T10:00:00Z"));
    }
}
