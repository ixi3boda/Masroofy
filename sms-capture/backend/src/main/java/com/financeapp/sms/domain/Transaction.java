package com.financeapp.sms.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.PrePersist;
import jakarta.persistence.PreUpdate;
import jakarta.persistence.Table;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.UUID;

/**
 * One income / expense / transfer record. "applied" says whether its amount is currently counted in the
 * account balance; only Ledger changes it, so balances stay correct after edits, rejections and retries.
 * If your app already has a Transaction entity, add the SMS columns to it and delete this class.
 */
@Entity
@Table(name = "transactions")
public class Transaction {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(name = "user_id", nullable = false) private Long userId;
    @Column(name = "account_id") private Long accountId;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 20) private TxType type;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 12) private TxStatus status = TxStatus.DRAFT;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 12) private TxSource source = TxSource.MANUAL;
    @Column(nullable = false, precision = 14, scale = 2) private BigDecimal amount;
    @Column(nullable = false, precision = 14, scale = 2) private BigDecimal fee = BigDecimal.ZERO;
    @Column(nullable = false, length = 3) private String currency = "EGP";
    @Column(name = "occurred_at", nullable = false) private Instant occurredAt;
    @Column(length = 200) private String merchant;
    /** card, instapay, wallet, bank_transfer, atm, other, unknown */
    @Column(length = 20) private String channel;
    /** The bank or app that sent the SMS / made the transaction. */
    @Column(length = 100) private String institution;
    @Column(name = "account_last4", length = 4) private String accountLast4;
    @Column(length = 60) private String category;
    /** Transfer between two of the user's own accounts: shown in history, not counted as spending. */
    @Column(name = "internal_transfer", nullable = false) private boolean internalTransfer;
    @Column(name = "transfer_group") private UUID transferGroup;
    @Column(name = "duplicate_of_id") private Long duplicateOfId;
    /** Balance the bank reported in the SMS, and (bank - app) after applying, when they differ. */
    @Column(name = "reported_balance", precision = 14, scale = 2) private BigDecimal reportedBalance;
    @Column(name = "balance_difference", precision = 14, scale = 2) private BigDecimal balanceDifference;
    @Column(precision = 4, scale = 3) private BigDecimal confidence;
    /** Comma-separated reasons a draft needs review, e.g. NO_ACCOUNT,POSSIBLE_DUPLICATE. */
    @Column(name = "review_reasons", length = 200) private String reviewReasons;
    @Column(name = "sms_message_id") private Long smsMessageId;
    @Column(nullable = false) private boolean applied;
    @Column(name = "created_at", nullable = false) private Instant createdAt;
    @Column(name = "updated_at", nullable = false) private Instant updatedAt;

    @PrePersist void onCreate() { createdAt = updatedAt = Instant.now(); }
    @PreUpdate void onUpdate() { updatedAt = Instant.now(); }

    public List<String> reviewReasonList() {
        return reviewReasons == null || reviewReasons.isBlank() ? new ArrayList<>() : new ArrayList<>(Arrays.asList(reviewReasons.split(",")));
    }
    public void addReviewReason(String r) {
        List<String> l = reviewReasonList();
        if (!l.contains(r)) l.add(r);
        reviewReasons = String.join(",", l);
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public void setUserId(Long userId) { this.userId = userId; }
    public Long getAccountId() { return accountId; }
    public void setAccountId(Long accountId) { this.accountId = accountId; }
    public TxType getType() { return type; }
    public void setType(TxType type) { this.type = type; }
    public TxStatus getStatus() { return status; }
    public void setStatus(TxStatus status) { this.status = status; }
    public TxSource getSource() { return source; }
    public void setSource(TxSource source) { this.source = source; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public BigDecimal getFee() { return fee; }
    public void setFee(BigDecimal fee) { this.fee = fee == null ? BigDecimal.ZERO : fee; }
    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }
    public Instant getOccurredAt() { return occurredAt; }
    public void setOccurredAt(Instant occurredAt) { this.occurredAt = occurredAt; }
    public String getMerchant() { return merchant; }
    public void setMerchant(String merchant) { this.merchant = merchant; }
    public String getChannel() { return channel; }
    public void setChannel(String channel) { this.channel = channel; }
    public String getInstitution() { return institution; }
    public void setInstitution(String institution) { this.institution = institution; }
    public String getAccountLast4() { return accountLast4; }
    public void setAccountLast4(String accountLast4) { this.accountLast4 = accountLast4; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public boolean isInternalTransfer() { return internalTransfer; }
    public void setInternalTransfer(boolean internalTransfer) { this.internalTransfer = internalTransfer; }
    public UUID getTransferGroup() { return transferGroup; }
    public void setTransferGroup(UUID transferGroup) { this.transferGroup = transferGroup; }
    public Long getDuplicateOfId() { return duplicateOfId; }
    public void setDuplicateOfId(Long duplicateOfId) { this.duplicateOfId = duplicateOfId; }
    public BigDecimal getReportedBalance() { return reportedBalance; }
    public void setReportedBalance(BigDecimal reportedBalance) { this.reportedBalance = reportedBalance; }
    public BigDecimal getBalanceDifference() { return balanceDifference; }
    public void setBalanceDifference(BigDecimal balanceDifference) { this.balanceDifference = balanceDifference; }
    public BigDecimal getConfidence() { return confidence; }
    public void setConfidence(BigDecimal confidence) { this.confidence = confidence; }
    public String getReviewReasons() { return reviewReasons; }
    public void setReviewReasons(String reviewReasons) { this.reviewReasons = reviewReasons; }
    public Long getSmsMessageId() { return smsMessageId; }
    public void setSmsMessageId(Long smsMessageId) { this.smsMessageId = smsMessageId; }
    public boolean isApplied() { return applied; }
    public void setApplied(boolean applied) { this.applied = applied; }
    public Instant getCreatedAt() { return createdAt; }
}
