package com.masroofy.backend.security;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.ErrorResponse;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.time.Clock;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Component;

/** Writes the standard {@link ErrorResponse} from the security filter chain, outside of MVC. */
@Component
public class ErrorResponseWriter {

    private final ObjectMapper objectMapper;
    private final Clock clock;

    public ErrorResponseWriter(ObjectMapper objectMapper, Clock clock) {
        this.objectMapper = objectMapper;
        this.clock = clock;
    }

    public void write(HttpServletRequest request, HttpServletResponse response, ErrorCode code, String message)
            throws IOException {
        if (response.isCommitted()) {
            return;
        }
        response.setStatus(code.status().value());
        response.setContentType(MediaType.APPLICATION_JSON_VALUE);
        response.setCharacterEncoding("UTF-8");
        ErrorResponse body = new ErrorResponse(Instant.now(clock), code.status().value(), code.name(),
                message, request.getRequestURI(), List.of(), Map.of());
        objectMapper.writeValue(response.getOutputStream(), body);
    }
}
