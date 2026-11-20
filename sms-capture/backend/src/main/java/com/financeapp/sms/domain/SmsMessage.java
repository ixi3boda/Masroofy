package com.financeapp.sms.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;

/**
 * Audit record of every SMS the phone uploaded. The text is kept only for transactions;
 * for anything else (OTPs, offers...) only a hash is stored.
 */
@Entity
@Table(name = "sms_messages")
public class SmsMessage {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(name = "user_id", nullable = false) private Long userId;
    @Column(nullable = false, length = 64) private String sender;
    @Column(length = 100) private String institution;
    @Column(columnDefinition = "text") private String body;
    @Column(name = "body_hash", nullable = false, length = 64) private String bodyHash;
    @Column(name = "received_at", nullable = false) private Instant receivedAt;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 12) private SmsStatus status;
    @Column(precision = 4, scale = 3) private BigDecimal confidence;
    @Column(name = "transaction_id") private Long transactionId;
    @Column(name = "created_at", nullable = false) private Instant createdAt;

    @PrePersist void onCreate() { createdAt = Instant.now(); }

    protected SmsMessage() {}
    public SmsMessage(Long userId, String sender, String bodyHash, Instant receivedAt) {
        this.userId = userId; this.sender = sender; this.bodyHash = bodyHash; this.receivedAt = receivedAt;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public String getSender() { return sender; }
    public String getInstitution() { return institution; }
    public void setInstitution(String institution) { this.institution = institution; }
    public String getBody() { return body; }
    public void setBody(String body) { this.body = body; }
    public String getBodyHash() { return bodyHash; }
    public Instant getReceivedAt() { return receivedAt; }
    public SmsStatus getStatus() { return status; }
    public void setStatus(SmsStatus status) { this.status = status; }
    public BigDecimal getConfidence() { return confidence; }
    public void setConfidence(BigDecimal confidence) { this.confidence = confidence; }
    public Long getTransactionId() { return transactionId; }
    public void setTransactionId(Long transactionId) { this.transactionId = transactionId; }
}
