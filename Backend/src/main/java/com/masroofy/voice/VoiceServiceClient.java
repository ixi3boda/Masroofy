package com.masroofy.voice;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.io.ByteArrayResource;
import org.springframework.http.MediaType;
import org.springframework.http.client.SimpleClientHttpRequestFactory;
import org.springframework.stereotype.Component;
import org.springframework.util.LinkedMultiValueMap;
import org.springframework.util.MultiValueMap;
import org.springframework.web.client.RestClient;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.databind.JsonNode;

import java.io.IOException;
import java.time.Duration;
import java.util.LinkedHashMap;
import java.util.Map;

/**
 * Calls the Python voice service (voice-service/voice_expense/api.py). It turns speech or text into
 * a draft transaction; it does not own the real data, PostgreSQL does.
 *
 * Errors are not caught here: an error answer from Python becomes HttpStatusCodeException and
 * "not running / timed out" becomes ResourceAccessException; GlobalExceptionHandler turns both
 * into the usual {"error_code", "message"} JSON.
 */
@Component
public class VoiceServiceClient {

    private final RestClient http;

    public VoiceServiceClient(@Value("${voice.service.url:http://localhost:8000}") String baseUrl,
                              @Value("${voice.service.connect-timeout-ms:5000}") long connectTimeoutMs,
                              @Value("${voice.service.read-timeout-ms:120000}") long readTimeoutMs) {
        SimpleClientHttpRequestFactory factory = new SimpleClientHttpRequestFactory();
        factory.setConnectTimeout(Duration.ofMillis(connectTimeoutMs));
        factory.setReadTimeout(Duration.ofMillis(readTimeoutMs));
        String url = baseUrl.endsWith("/") ? baseUrl.substring(0, baseUrl.length() - 1) : baseUrl;
        this.http = RestClient.builder().baseUrl(url).requestFactory(factory).build();
    }

    public JsonNode health() {
        return http.get().uri("/health").retrieve().body(JsonNode.class);
    }

    /** POST /v1/expenses/parse-text -> ExpenseDraft */
    public JsonNode parseText(String text, String referenceTime, String extractor) {
        Map<String, Object> body = new LinkedHashMap<>();
        body.put("text", text);
        if (hasText(referenceTime)) body.put("reference_time", referenceTime);
        if (hasText(extractor)) body.put("extractor", extractor);
        return http.post().uri("/v1/expenses/parse-text")
                .contentType(MediaType.APPLICATION_JSON)
                .body(body)
                .retrieve()
                .body(JsonNode.class);
    }

    /** POST /v1/expenses/parse-audio (multipart) -> ExpenseDraft */
    public JsonNode parseAudio(MultipartFile file, String referenceTime, String language, String extractor) throws IOException {
        // Keep the file name: the voice service picks the audio format from the extension (.m4a, .wav...).
        String original = file.getOriginalFilename();
        String filename = hasText(original) ? original : "recording.m4a";
        ByteArrayResource audio = new ByteArrayResource(file.getBytes()) {
            @Override
            public String getFilename() {
                return filename;
            }
        };
        MultiValueMap<String, Object> parts = new LinkedMultiValueMap<>();
        parts.add("file", audio);
        if (hasText(referenceTime)) parts.add("reference_time", referenceTime);
        if (hasText(language)) parts.add("language", language);
        if (hasText(extractor)) parts.add("extractor", extractor);
        return http.post().uri("/v1/expenses/parse-audio")
                .contentType(MediaType.MULTIPART_FORM_DATA)
                .body(parts)
                .retrieve()
                .body(JsonNode.class);
    }

    /**
     * POST /v1/expenses/confirm {draft, corrections} -> the final values. Python validates the
     * corrections and keeps a log of which fields users corrected (for the accuracy report).
     */
    public JsonNode confirm(JsonNode confirmRequest) {
        return http.post().uri("/v1/expenses/confirm")
                .contentType(MediaType.APPLICATION_JSON)
                .body(confirmRequest)
                .retrieve()
                .body(JsonNode.class);
    }

    private static boolean hasText(String s) {
        return s != null && !s.isBlank();
    }
}
