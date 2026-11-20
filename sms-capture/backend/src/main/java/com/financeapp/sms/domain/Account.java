package com.financeapp.sms.domain;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import java.math.BigDecimal;

/**
 * A user's money source. If your app already has an Account entity, add the two SMS columns
 * (institution, last4) to it and delete this class.
 */
@Entity
@Table(name = "accounts")
public class Account {
    @Id @GeneratedValue(strategy = GenerationType.IDENTITY) private Long id;
    @Column(name = "user_id", nullable = false) private Long userId;
    @Column(nullable = false, length = 100) private String name;
    @Enumerated(EnumType.STRING) @Column(nullable = false, length = 16) private AccountType type;
    /** Bank or app that sends SMS for this account, e.g. "NileBank", "Cairo Wallet". */
    @Column(length = 100) private String institution;
    /** Last digits of the card or account as shown in SMS (****1234, xx1234). */
    @Column(length = 4) private String last4;
    @Column(nullable = false, length = 3) private String currency = "EGP";
    @Column(nullable = false, precision = 14, scale = 2) private BigDecimal balance = BigDecimal.ZERO;

    protected Account() {}
    public Account(Long userId, String name, AccountType type, String institution, String last4, BigDecimal balance) {
        this.userId = userId; this.name = name; this.type = type; this.institution = institution; this.last4 = last4;
        this.balance = balance;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public Long getUserId() { return userId; }
    public String getName() { return name; }
    public AccountType getType() { return type; }
    public String getInstitution() { return institution; }
    public void setInstitution(String institution) { this.institution = institution; }
    public String getLast4() { return last4; }
    public void setLast4(String last4) { this.last4 = last4; }
    public String getCurrency() { return currency; }
    public BigDecimal getBalance() { return balance; }
    public void setBalance(BigDecimal balance) { this.balance = balance; }
}
