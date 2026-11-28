package com.masroofy.voice;

import com.masroofy.transaction.Transaction;
import com.masroofy.transaction.TransactionService;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.multipart.MultipartFile;
import tools.jackson.databind.JsonNode;

import java.io.IOException;
import java.net.URI;

/**
 * Voice entry, used by the mobile app:
 *
 *   GET  /api/voice-expenses/health        status of the Python voice service
 *   POST /api/voice-expenses/parse-text    JSON {"text": "...", "reference_time": "2026-11-27T20:58:00Z"}
 *   POST /api/voice-expenses/parse-audio   multipart: file, reference_time?, language?, extractor?
 *   POST /api/voice-expenses/confirm       JSON {"draft": {...}, "corrections": {"amount": "160"}}
 *
 * parse-* return a DRAFT (nothing is saved). confirm saves the transaction in PostgreSQL and
 * returns it (201), exactly like GET /api/transactions/{id}.
 */
@RestController
@RequestMapping("/api/voice-expenses")
public class VoiceExpenseController {

    private final VoiceServiceClient voice;
    private final TransactionService transactions;

    public VoiceExpenseController(VoiceServiceClient voice, TransactionService transactions) {
        this.voice = voice;
        this.transactions = transactions;
    }

    @GetMapping("/health")
    public JsonNode health() {
        return voice.health();
    }

    @PostMapping(value = "/parse-text", consumes = MediaType.APPLICATION_JSON_VALUE)
    public JsonNode parseText(@RequestBody ParseTextRequest body) {
        return voice.parseText(body.text(), body.referenceTime(), body.extractor());
    }

    @PostMapping(value = "/parse-audio", consumes = MediaType.MULTIPART_FORM_DATA_VALUE)
    public JsonNode parseAudio(@RequestParam("file") MultipartFile file,
                               @RequestParam(value = "reference_time", required = false) String referenceTime,
                               @RequestParam(value = "language", required = false) String language,
                               @RequestParam(value = "extractor", required = false) String extractor) throws IOException {
        return voice.parseAudio(file, referenceTime, language, extractor);
    }

    @PostMapping(value = "/confirm", consumes = MediaType.APPLICATION_JSON_VALUE)
    public ResponseEntity<Transaction> confirm(@RequestBody JsonNode confirmRequest) {
        JsonNode confirmed = voice.confirm(confirmRequest);   // validates + applies the corrections
        Transaction saved = transactions.saveConfirmedVoice(confirmed);
        return ResponseEntity.created(URI.create("/api/transactions/" + saved.getId())).body(saved);
    }
}
