package com.masroofy.backend.config;

import com.masroofy.backend.controller.ApiErrorController;
import com.masroofy.backend.exception.ErrorCode;
import java.io.IOException;
import java.io.Writer;
import java.time.Instant;
import org.apache.catalina.connector.Request;
import org.apache.catalina.connector.Response;
import org.apache.catalina.valves.ErrorReportValve;

/**
 * Tomcat's last-resort error page, used for requests Tomcat rejects before Spring sees them (for example a
 * {@code %00} in the URL). Writes the documented {@code ErrorResponse} JSON instead of Tomcat's HTML page.
 * Everything Spring handles never reaches it: those responses already have a body.
 */
public class JsonErrorReportValve extends ErrorReportValve {

    @Override
    protected void report(Request request, Response response, Throwable throwable) {
        int status = response.getStatus();
        if (status < 400 || response.getContentWritten() > 0 || !response.setErrorReported()) {
            return;
        }
        ErrorCode code = ApiErrorController.toErrorCode(status, throwable);
        String path = request.getRequestURI() == null ? "" : request.getRequestURI();
        // Tomcat only rejects requests itself for a bad URL or bad headers, never because of the body.
        String message = code == ErrorCode.MALFORMED_REQUEST ? "The request is malformed." : code.defaultMessage();
        String body = "{\"timestamp\":\"" + Instant.now() + "\",\"status\":" + code.status().value()
                + ",\"code\":\"" + code.name() + "\",\"message\":" + quote(message)
                + ",\"path\":" + quote(path) + "}";
        try {
            response.setStatus(code.status().value());
            response.setContentType("application/json");
            response.setCharacterEncoding("UTF-8");
            Writer writer = response.getReporter();
            if (writer != null) {
                writer.write(body);
                response.finishResponse();
            }
        } catch (IOException | IllegalStateException e) {
            // The connection is already gone; nothing useful left to do.
        }
    }

    static String quote(String value) {
        StringBuilder out = new StringBuilder(value.length() + 2).append('"');
        for (char c : value.toCharArray()) {
            switch (c) {
                case '"' -> out.append("\\\"");
                case '\\' -> out.append("\\\\");
                default -> {
                    if (c < 0x20) {
                        out.append(String.format("\\u%04x", (int) c));
                    } else {
                        out.append(c);
                    }
                }
            }
        }
        return out.append('"').toString();
    }
}
