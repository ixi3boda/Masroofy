package com.masroofy.common;

/** Every error the API returns has this shape: {"error_code": "...", "message": "..."} (same as the Python service). */
public record ErrorResponse(String errorCode, String message) {
}
