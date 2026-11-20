package com.financeapp.sms.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;

/** A user's own mapping from an SMS sender ID to the bank or app it belongs to (overrides the defaults). */
@Entity
@Table(name = "sms_senders")
public class SmsSender {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(name = "user_id", nullable = false) private Long userId;
    /** Normalised sender ID (see SenderRegistry.normalize). */
    @Column(name = "sender_id", nullable = false, length = 64) private String senderId;
    @Column(nullable = false, length = 100) private String institution;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 16) private AccountType kind;
    @Column(nullable = false) private boolean enabled = true;

    protected SmsSender() {}
    public SmsSender(Long userId, String senderId, String institution, AccountType kind, boolean enabled) {
        this.userId = userId; this.senderId = senderId; this.institution = institution; this.kind = kind; this.enabled = enabled;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public String getSenderId() { return senderId; }
    public String getInstitution() { return institution; }
    public void setInstitution(String institution) { this.institution = institution; }
    public AccountType getKind() { return kind; }
    public void setKind(AccountType kind) { this.kind = kind; }
    public boolean isEnabled() { return enabled; }
    public void setEnabled(boolean enabled) { this.enabled = enabled; }
}
