package com.masroofy.transaction;

import jakarta.validation.Valid;
import org.springframework.format.annotation.DateTimeFormat;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.DeleteMapping;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RequestParam;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestController;

import java.net.URI;
import java.time.LocalDate;
import java.time.YearMonth;
import java.util.List;

/**
 * Saved transactions.
 *
 *   GET    /api/transactions?from=2026-11-01&to=2026-11-30&category=transport&type=expense&limit=100
 *   GET    /api/transactions/summary?month=2026-11      (default: current month)
 *   GET    /api/transactions/categories
 *   GET    /api/transactions/{id}
 *   POST   /api/transactions                            add without voice
 *   PUT    /api/transactions/{id}                       edit
 *   DELETE /api/transactions/{id}
 *
 * Voice entries are saved by POST /api/voice-expenses/confirm (see VoiceExpenseController).
 */
@RestController
@RequestMapping("/api/transactions")
public class TransactionController {

    private final TransactionService service;

    public TransactionController(TransactionService service) {
        this.service = service;
    }

    @GetMapping
    public List<Transaction> list(
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate from,
            @RequestParam(required = false) @DateTimeFormat(iso = DateTimeFormat.ISO.DATE) LocalDate to,
            @RequestParam(required = false) String category,
            @RequestParam(required = false) String type,
            @RequestParam(defaultValue = "100") int limit) {
        return service.list(from, to, category, type, limit);
    }

    @GetMapping("/summary")
    public MonthlySummary summary(@RequestParam(required = false) YearMonth month) {
        return service.summary(month);
    }

    @GetMapping("/categories")
    public List<String> categories() {
        return Categories.ALL;
    }

    @GetMapping("/{id}")
    public Transaction get(@PathVariable Long id) {
        return service.get(id);
    }

    @PostMapping
    public ResponseEntity<Transaction> create(@Valid @RequestBody TransactionRequest request) {
        Transaction saved = service.create(request);
        return ResponseEntity.created(URI.create("/api/transactions/" + saved.getId())).body(saved);
    }

    @PutMapping("/{id}")
    public Transaction update(@PathVariable Long id, @Valid @RequestBody TransactionRequest request) {
        return service.update(id, request);
    }

    @DeleteMapping("/{id}")
    @ResponseStatus(HttpStatus.NO_CONTENT)
    public void delete(@PathVariable Long id) {
        service.delete(id);
    }
}
