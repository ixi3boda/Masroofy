package com.financeapp.sms.web;

import com.financeapp.sms.config.SmsProperties;
import com.financeapp.sms.domain.AccountType;
import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.security.CurrentUser;
import com.financeapp.sms.service.IngestResult;
import com.financeapp.sms.service.SenderRegistry;
import com.financeapp.sms.service.SmsIngestService;
import com.financeapp.sms.service.SmsReviewService;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import org.springframework.dao.DataIntegrityViolationException;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.PostMapping;
import org.springframework.web.bind.annotation.PutMapping;
import org.springframework.web.bind.annotation.RequestBody;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

/**
 * POST /api/sms/ingest                      phone uploads captured SMS (or the user pastes one)
 * GET  /api/sms/senders                     bank/app sender IDs; the phone's allow-list
 * PUT  /api/sms/senders                     user adds or renames a sender
 * GET  /api/sms/review                      drafts waiting for review
 * POST /api/sms/transactions/{id}/confirm   confirm or correct (body optional)
 * POST /api/sms/transactions/{id}/reject    reject (reverses the balance if it was applied)
 */
@RestController
@RequestMapping("/api/sms")
public class SmsController {

    public record IncomingSmsDto(String sender, String body, Long receivedAt) {}
    public record IngestRequest(List<IncomingSmsDto> messages) {}
    public record IngestResponse(List<IngestResult> results) {}
    public record SenderUpsert(String senderId, String institution, String kind, Boolean enabled) {}
    public record ConfirmRequest(Long accountId, String type, BigDecimal amount, BigDecimal fee, String merchant,
                                 Instant occurredAt, String category) {}
    public record TransactionView(Long id, String status, String type, BigDecimal amount, BigDecimal fee, String currency,
                                  Instant occurredAt, String merchant, String channel, String institution, Long accountId,
                                  String accountLast4, boolean internalTransfer, Long duplicateOfId, BigDecimal reportedBalance,
                                  BigDecimal balanceDifference, BigDecimal confidence, List<String> reviewReasons) {
        static TransactionView of(Transaction t) {
            return new TransactionView(t.getId(), t.getStatus().name(), t.getType().name(), t.getAmount(), t.getFee(),
                    t.getCurrency(), t.getOccurredAt(), t.getMerchant(), t.getChannel(), t.getInstitution(), t.getAccountId(),
                    t.getAccountLast4(), t.isInternalTransfer(), t.getDuplicateOfId(), t.getReportedBalance(),
                    t.getBalanceDifference(), t.getConfidence(), t.reviewReasonList());
        }
    }

    private final SmsIngestService ingest;
    private final SmsReviewService review;
    private final SenderRegistry senders;
    private final SmsProperties props;
    private final CurrentUser currentUser;

    public SmsController(SmsIngestService ingest, SmsReviewService review, SenderRegistry senders, SmsProperties props,
                         CurrentUser currentUser) {
        this.ingest = ingest; this.review = review; this.senders = senders; this.props = props; this.currentUser = currentUser;
    }

    @PostMapping("/ingest")
    public IngestResponse ingest(@RequestBody IngestRequest req) {
        Long uid = currentUser.id();
        if (req == null || req.messages() == null || req.messages().isEmpty()) throw bad("messages is empty");
        if (req.messages().size() > props.getMaxBatch()) throw bad("at most " + props.getMaxBatch() + " messages per request");
        List<IngestResult> out = new ArrayList<>();
        for (IncomingSmsDto m : req.messages()) {
            if (m == null || m.sender() == null || m.sender().isBlank() || m.body() == null || m.body().isBlank()) throw bad("sender and body are required");
            if (m.sender().length() > 64 || m.body().length() > props.getMaxBodyLength()) throw bad("sender or body too long");
            long at = m.receivedAt() != null ? m.receivedAt() : System.currentTimeMillis();
            try {
                out.add(ingest.ingestOne(uid, new SmsIngestService.IncomingSms(m.sender(), m.body(), at)));
            } catch (DataIntegrityViolationException race) {   // same SMS uploaded twice at the same moment
                out.add(IngestResult.alreadyReceived());
            }
        }
        return new IngestResponse(out);
    }

    @GetMapping("/senders")
    public List<SenderRegistry.SenderView> senders() { return senders.list(currentUser.id()); }

    @PutMapping("/senders")
    public SenderRegistry.SenderView upsertSender(@RequestBody SenderUpsert s) {
        AccountType kind;
        try { kind = AccountType.valueOf(s.kind() == null ? "BANK" : s.kind().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException e) { throw bad("kind must be CASH, CARD, BANK or WALLET"); }
        try { return senders.upsert(currentUser.id(), s.senderId(), s.institution(), kind, s.enabled() == null || s.enabled()); }
        catch (IllegalArgumentException e) { throw bad(e.getMessage()); }
    }

    @GetMapping("/review")
    public List<TransactionView> drafts() {
        return review.drafts(currentUser.id()).stream().map(TransactionView::of).toList();
    }

    @PostMapping("/transactions/{id}/confirm")
    public TransactionView confirm(@PathVariable("id") Long id, @RequestBody(required = false) ConfirmRequest r) {
        SmsReviewService.Edits e = r == null ? null
                : new SmsReviewService.Edits(r.accountId(), r.type(), r.amount(), r.fee(), r.merchant(), r.occurredAt(), r.category());
        return TransactionView.of(review.confirm(currentUser.id(), id, e));
    }

    @PostMapping("/transactions/{id}/reject")
    public TransactionView reject(@PathVariable("id") Long id) {
        return TransactionView.of(review.reject(currentUser.id(), id));
    }

    private static ResponseStatusException bad(String msg) { return new ResponseStatusException(HttpStatus.BAD_REQUEST, msg); }
}
