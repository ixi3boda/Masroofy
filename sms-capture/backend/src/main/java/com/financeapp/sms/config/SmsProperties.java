package com.financeapp.sms.config;

import com.financeapp.sms.domain.AccountType;
import java.util.ArrayList;
import java.util.List;
import org.springframework.boot.context.properties.ConfigurationProperties;

/**
 * Settings under "app.sms" in application.yml. Defaults work out of the box.
 *
 * app:
 *   sms:
 *     auto-confirm: true                 # false = every SMS becomes a draft (the proposal's "transaction drafts")
 *     auto-confirm-min-confidence: 0.85
 *     senders:                           # replaces the default list below
 *       - { id: "NileBank", name: "NileBank", kind: BANK }
 */
@ConfigurationProperties(prefix = "app.sms")
public class SmsProperties {
    /** Apply clear, high-confidence SMS transactions to the balance immediately; everything else waits for review. */
    private boolean autoConfirm = true;
    private double autoConfirmMinConfidence = 0.85;
    /** Same amount + type + account + merchant within this many minutes = possible duplicate (review). */
    private int duplicateWindowMinutes = 10;
    /** Opposite transfers of the same amount between two of the user's accounts within this window are linked. */
    private int transferMatchWindowMinutes = 30;
    /** Bank SMS show local time without a zone. */
    private String zone = "Africa/Cairo";
    /** Keep the SMS text of transactions for audit/re-parsing. Non-transactions (OTPs, offers) are never stored. */
    private boolean storeTransactionText = true;
    private int maxBatch = 50;
    private int maxBodyLength = 2000;
    /** Known SMS senders: sender ID shown on the phone -> bank/app name. Users can add their own via the API. */
    private List<Sender> senders = new ArrayList<>(List.of(
            new Sender("NileBank", "NileBank", AccountType.BANK),
            new Sender("Luxor Bank", "Luxor Bank", AccountType.BANK),
            new Sender("SphinxCard", "SphinxCard", AccountType.CARD),
            new Sender("Giza Finance", "Giza Finance", AccountType.CARD),
            new Sender("DeltaPay", "DeltaPay", AccountType.BANK),
            new Sender("Cairo Wallet", "Cairo Wallet", AccountType.WALLET),
            new Sender("Pharos Pay", "Pharos Pay", AccountType.WALLET),
            new Sender("Sinai Pay", "Sinai Pay", AccountType.WALLET)));

    public static class Sender {
        private String id;
        private String name;
        private AccountType kind = AccountType.BANK;
        public Sender() {}
        public Sender(String id, String name, AccountType kind) { this.id = id; this.name = name; this.kind = kind; }
        public String getId() { return id; }
        public void setId(String id) { this.id = id; }
        public String getName() { return name; }
        public void setName(String name) { this.name = name; }
        public AccountType getKind() { return kind; }
        public void setKind(AccountType kind) { this.kind = kind; }
    }

    public boolean isAutoConfirm() { return autoConfirm; }
    public void setAutoConfirm(boolean autoConfirm) { this.autoConfirm = autoConfirm; }
    public double getAutoConfirmMinConfidence() { return autoConfirmMinConfidence; }
    public void setAutoConfirmMinConfidence(double v) { this.autoConfirmMinConfidence = v; }
    public int getDuplicateWindowMinutes() { return duplicateWindowMinutes; }
    public void setDuplicateWindowMinutes(int v) { this.duplicateWindowMinutes = v; }
    public int getTransferMatchWindowMinutes() { return transferMatchWindowMinutes; }
    public void setTransferMatchWindowMinutes(int v) { this.transferMatchWindowMinutes = v; }
    public String getZone() { return zone; }
    public void setZone(String zone) { this.zone = zone; }
    public boolean isStoreTransactionText() { return storeTransactionText; }
    public void setStoreTransactionText(boolean v) { this.storeTransactionText = v; }
    public int getMaxBatch() { return maxBatch; }
    public void setMaxBatch(int maxBatch) { this.maxBatch = maxBatch; }
    public int getMaxBodyLength() { return maxBodyLength; }
    public void setMaxBodyLength(int maxBodyLength) { this.maxBodyLength = maxBodyLength; }
    public List<Sender> getSenders() { return senders; }
    public void setSenders(List<Sender> senders) { this.senders = senders; }
}
