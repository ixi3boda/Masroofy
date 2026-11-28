package com.masroofy.common;

import com.masroofy.transaction.TransactionRepository;
import com.masroofy.voice.VoiceServiceClient;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.LinkedHashMap;
import java.util.Map;

/** GET /api/health — is everything the app needs reachable? Useful when "nothing works". */
@RestController
public class HealthController {

    private final TransactionRepository repository;
    private final VoiceServiceClient voice;

    public HealthController(TransactionRepository repository, VoiceServiceClient voice) {
        this.repository = repository;
        this.voice = voice;
    }

    @GetMapping("/api/health")
    public Map<String, Object> health() {
        Map<String, Object> out = new LinkedHashMap<>();
        out.put("status", "ok");
        try {
            out.put("database", "ok (" + repository.count() + " transactions)");
        } catch (RuntimeException e) {
            out.put("status", "degraded");
            out.put("database", "unavailable: " + e.getMessage());
        }
        try {
            out.put("voice_service", "ok (asr: " + voice.health().path("asr_backend").asString() + ")");
        } catch (RuntimeException e) {
            out.put("status", "degraded");
            out.put("voice_service", "unavailable: start it with uvicorn voice_expense.api:app --host 127.0.0.1 --port 8000");
        }
        return out;
    }
}
