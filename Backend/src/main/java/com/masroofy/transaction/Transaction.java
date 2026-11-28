package com.masroofy.transaction;

import com.fasterxml.jackson.annotation.JsonFormat;
import jakarta.persistence.Column;
import jakarta.persistence.Convert;
import jakarta.persistence.Entity;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Index;
import jakarta.persistence.Table;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.UpdateTimestamp;

import java.math.BigDecimal;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.util.ArrayList;
import java.util.List;

/** One saved transaction (table "transactions"). JSON field names are snake_case, e.g. payment_method. */
@Entity
@Table(name = "transactions", indexes = @Index(name = "idx_transactions_user_date", columnList = "user_id, tx_date"))
public class Transaction {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    /** Owner (see CurrentUser). Null while the app has no login. */
    @Column(name = "user_id", length = 64)
    private String userId;

    /** "expense" | "income" */
    @Column(name = "transaction_type", nullable = false, length = 10)
    private String transactionType;

    @Column(nullable = false, precision = 14, scale = 2)
    private BigDecimal amount;

    /** ISO code, e.g. EGP, USD */
    @Column(nullable = false, length = 3)
    private String currency;

    @Column(length = 120)
    private String merchant;

    /** One of Categories.ALL */
    @Column(nullable = false, length = 40)
    private String category;

    @Column(name = "tx_date", nullable = false)
    private LocalDate date;

    @JsonFormat(pattern = "HH:mm")
    @Column(name = "tx_time")
    private LocalTime time;

    /** "cash" | "card" | "wallet" | "unknown" */
    @Column(name = "payment_method", nullable = false, length = 10)
    private String paymentMethod;

    @Column(length = 500)
    private String note;

    /** How it was entered: "voice" (recording), "text" (typed sentence) or "manual" (form only). */
    @Column(nullable = false, length = 10)
    private String source;

    /** What the user said or typed (voice/text only). */
    @Column(length = 2000)
    private String transcript;

    /** "ar" | "en" | "mixed" (voice/text only). */
    @Column(length = 10)
    private String language;

    @Column(name = "extraction_method", length = 30)
    private String extractionMethod;

    /** Fields the user corrected in the review screen before saving. */
    @Convert(converter = StringListConverter.class)
    @Column(name = "edited_fields", length = 200)
    private List<String> editedFields = new ArrayList<>();

    /** Id of the matching record in the Python service's correction log (eval/confirmed_report.py). */
    @Column(name = "voice_record_id")
    private Long voiceRecordId;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private Instant createdAt;

    @UpdateTimestamp
    @Column(name = "updated_at", nullable = false)
    private Instant updatedAt;

    public Long getId() { return id; }
    public String getUserId() { return userId; }
    public void setUserId(String userId) { this.userId = userId; }
    public String getTransactionType() { return transactionType; }
    public void setTransactionType(String transactionType) { this.transactionType = transactionType; }
    public BigDecimal getAmount() { return amount; }
    public void setAmount(BigDecimal amount) { this.amount = amount; }
    public String getCurrency() { return currency; }
    public void setCurrency(String currency) { this.currency = currency; }
    public String getMerchant() { return merchant; }
    public void setMerchant(String merchant) { this.merchant = merchant; }
    public String getCategory() { return category; }
    public void setCategory(String category) { this.category = category; }
    public LocalDate getDate() { return date; }
    public void setDate(LocalDate date) { this.date = date; }
    public LocalTime getTime() { return time; }
    public void setTime(LocalTime time) { this.time = time; }
    public String getPaymentMethod() { return paymentMethod; }
    public void setPaymentMethod(String paymentMethod) { this.paymentMethod = paymentMethod; }
    public String getNote() { return note; }
    public void setNote(String note) { this.note = note; }
    public String getSource() { return source; }
    public void setSource(String source) { this.source = source; }
    public String getTranscript() { return transcript; }
    public void setTranscript(String transcript) { this.transcript = transcript; }
    public String getLanguage() { return language; }
    public void setLanguage(String language) { this.language = language; }
    public String getExtractionMethod() { return extractionMethod; }
    public void setExtractionMethod(String extractionMethod) { this.extractionMethod = extractionMethod; }
    public List<String> getEditedFields() { return editedFields; }
    public void setEditedFields(List<String> editedFields) { this.editedFields = editedFields == null ? new ArrayList<>() : new ArrayList<>(editedFields); }
    public Long getVoiceRecordId() { return voiceRecordId; }
    public void setVoiceRecordId(Long voiceRecordId) { this.voiceRecordId = voiceRecordId; }
    public Instant getCreatedAt() { return createdAt; }
    public Instant getUpdatedAt() { return updatedAt; }
}
