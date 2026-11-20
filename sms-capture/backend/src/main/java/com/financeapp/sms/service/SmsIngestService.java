package com.financeapp.sms.service;

import com.financeapp.sms.config.SmsProperties;
import com.financeapp.sms.domain.Account;
import com.financeapp.sms.domain.SmsMessage;
import com.financeapp.sms.domain.SmsStatus;
import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.domain.TxSource;
import com.financeapp.sms.domain.TxStatus;
import com.financeapp.sms.domain.TxType;
import com.financeapp.sms.ledger.Ledger;
import com.financeapp.sms.parser.ParsedSms;
import com.financeapp.sms.parser.SmsParser;
import com.financeapp.sms.repo.AccountKey;
import com.financeapp.sms.repo.AccountRepository;
import com.financeapp.sms.repo.SmsMessageRepository;
import com.financeapp.sms.repo.TransactionRepository;
import java.math.BigDecimal;
import java.math.RoundingMode;
import java.nio.charset.StandardCharsets;
import java.security.MessageDigest;
import java.security.NoSuchAlgorithmException;
import java.time.Duration;
import java.time.Instant;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.util.HexFormat;
import java.util.List;
import java.util.Objects;
import java.util.Optional;
import java.util.UUID;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

/**
 * Turns one incoming SMS into a transaction and, when it is clear, updates the account balance.
 *
 *   SMS -> already uploaded? -> parse -> not a transaction? store hash only, stop
 *       -> bank/app from sender ID -> match account -> date/time -> duplicate check -> own-transfer link
 *       -> nothing to review and auto-confirm on? lock account row, apply to balance (CONFIRMED)
 *       -> otherwise DRAFT with review reasons (balance untouched until the user confirms)
 */
@Service
public class SmsIngestService {

    public record IncomingSms(String sender, String body, long receivedAtMillis) {}

    private final SmsParser parser;
    private final SmsProperties props;
    private final SenderRegistry senders;
    private final AccountMatcher matcher;
    private final AccountRepository accounts;
    private final TransactionRepository transactions;
    private final SmsMessageRepository messages;

    public SmsIngestService(SmsParser parser, SmsProperties props, SenderRegistry senders, AccountMatcher matcher,
                            AccountRepository accounts, TransactionRepository transactions, SmsMessageRepository messages) {
        this.parser = parser; this.props = props; this.senders = senders; this.matcher = matcher;
        this.accounts = accounts; this.transactions = transactions; this.messages = messages;
    }

    /** One SMS per database transaction, so one bad message never rolls back the others. */
    @Transactional
    public IngestResult ingestOne(Long userId, IncomingSms sms) {
        String sender = sms.sender().trim();
        Instant receivedAt = Instant.ofEpochMilli(sms.receivedAtMillis());
        String hash = sha256(sender + "\n" + sms.receivedAtMillis() + "\n" + sms.body());
        if (messages.existsByUserIdAndBodyHash(userId, hash)) return IngestResult.alreadyReceived();

        Optional<SenderRegistry.Institution> inst = senders.resolve(userId, sender);
        String institution = inst.map(SenderRegistry.Institution::name).orElse(sender);
        SmsMessage msg = new SmsMessage(userId, sender, hash, receivedAt);
        msg.setInstitution(institution);

        ParsedSms p = parser.parse(sms.body());
        msg.setConfidence(BigDecimal.valueOf(p.confidence).setScale(3, RoundingMode.HALF_UP));
        if (!p.isTransaction) {                       // OTPs, offers, declined payments...: keep no text
            msg.setStatus(SmsStatus.IGNORED);
            messages.save(msg);
            return IngestResult.ignored(institution);
        }
        if (props.isStoreTransactionText()) msg.setBody(sms.body());
        msg.setStatus(SmsStatus.DRAFT);
        msg = messages.save(msg);

        Optional<AccountKey> acc = matcher.match(userId, institution, p.accountLast4);
        Transaction t = new Transaction();
        t.setUserId(userId);
        t.setSource(TxSource.SMS);
        t.setStatus(TxStatus.DRAFT);
        t.setType(TxType.fromLabel(p.type));
        t.setAmount(money(p.amount));
        t.setFee(p.fee == null ? BigDecimal.ZERO : money(p.fee));
        t.setCurrency(p.currency != null ? p.currency : acc.map(AccountKey::currency).orElse("EGP"));
        t.setOccurredAt(resolveOccurredAt(p, receivedAt, ZoneId.of(props.getZone())));
        t.setMerchant(p.merchant);
        t.setChannel(p.channel);
        t.setInstitution(institution);
        t.setAccountLast4(p.accountLast4);
        t.setReportedBalance(p.balanceAfter == null ? null : money(p.balanceAfter));
        t.setConfidence(msg.getConfidence());
        t.setSmsMessageId(msg.getId());
        acc.ifPresent(a -> t.setAccountId(a.id()));

        if (inst.isEmpty()) t.addReviewReason("UNKNOWN_SENDER");
        if (acc.isEmpty()) t.addReviewReason("NO_ACCOUNT");
        if (t.getType() == TxType.OTHER) t.addReviewReason("UNKNOWN_TYPE");
        if (p.confidence < props.getAutoConfirmMinConfidence()) t.addReviewReason("LOW_CONFIDENCE");
        if (acc.isPresent() && !t.getCurrency().equalsIgnoreCase(acc.get().currency())) t.addReviewReason("FOREIGN_CURRENCY");
        findDuplicate(t).ifPresent(d -> { t.setDuplicateOfId(d.getId()); t.addReviewReason("POSSIBLE_DUPLICATE"); });

        Transaction saved = transactions.save(t);
        linkOwnTransfer(saved);

        if (props.isAutoConfirm() && saved.reviewReasonList().isEmpty()) {
            Account account = accounts.lockByIdAndUserId(saved.getAccountId(), userId).orElseThrow();
            Ledger.apply(account, saved);
            recordBalanceDifference(account, saved);
            msg.setStatus(SmsStatus.APPLIED);
        }
        msg.setTransactionId(saved.getId());
        return new IngestResult(saved.getStatus() == TxStatus.CONFIRMED ? "APPLIED" : "DRAFT", saved.getId(), institution,
                saved.getType().name(), saved.getAmount(), saved.getCurrency(), saved.getOccurredAt(), saved.getAccountId(),
                saved.reviewReasonList());
    }

    /** Same amount, type, account and merchant a few minutes apart -> review instead of counting twice. */
    private Optional<Transaction> findDuplicate(Transaction t) {
        Duration w = Duration.ofMinutes(props.getDuplicateWindowMinutes());
        return transactions.findNear(t.getUserId(), t.getAmount(), TxStatus.REJECTED,
                        t.getOccurredAt().minus(w), t.getOccurredAt().plus(w)).stream()
                .filter(o -> o.getType() == t.getType() && Objects.equals(o.getAccountId(), t.getAccountId()))
                .filter(o -> o.getMerchant() == null || t.getMerchant() == null || o.getMerchant().equalsIgnoreCase(t.getMerchant()))
                .findFirst();
    }

    /** transfer_out from one of the user's accounts + transfer_in of the same amount to another = own transfer. */
    private void linkOwnTransfer(Transaction t) {
        if (t.getAccountId() == null || (t.getType() != TxType.TRANSFER_OUT && t.getType() != TxType.TRANSFER_IN)) return;
        TxType opposite = t.getType() == TxType.TRANSFER_OUT ? TxType.TRANSFER_IN : TxType.TRANSFER_OUT;
        Duration w = Duration.ofMinutes(props.getTransferMatchWindowMinutes());
        transactions.findNear(t.getUserId(), t.getAmount(), TxStatus.REJECTED, t.getOccurredAt().minus(w), t.getOccurredAt().plus(w))
                .stream()
                .filter(o -> o.getType() == opposite && o.getTransferGroup() == null && o.getAccountId() != null
                        && !o.getAccountId().equals(t.getAccountId()))
                .findFirst()
                .ifPresent(o -> {
                    UUID group = UUID.randomUUID();
                    for (Transaction x : List.of(t, o)) { x.setTransferGroup(group); x.setInternalTransfer(true); }
                    transactions.save(o);
                });
    }

    static void recordBalanceDifference(Account account, Transaction t) {
        if (t.getReportedBalance() == null) return;
        BigDecimal diff = t.getReportedBalance().subtract(account.getBalance());
        t.setBalanceDifference(diff.signum() == 0 ? null : diff);
    }

    /**
     * SMS date/time are Egyptian local time. Date + time -> that moment; date only -> the time the SMS
     * arrived if same day, else start of that day; nothing -> arrival time. Implausible dates fall back to arrival.
     */
    static Instant resolveOccurredAt(ParsedSms p, Instant receivedAt, ZoneId zone) {
        if (p.date == null) return receivedAt;
        ZonedDateTime when;
        if (p.time != null) when = LocalDateTime.of(p.date, p.time).atZone(zone);
        else if (p.date.equals(receivedAt.atZone(zone).toLocalDate())) return receivedAt;
        else when = p.date.atStartOfDay(zone);
        Instant i = when.toInstant();
        if (i.isAfter(receivedAt.plus(Duration.ofDays(1))) || i.isBefore(receivedAt.minus(Duration.ofDays(400)))) return receivedAt;
        return i;
    }

    static BigDecimal money(double v) { return BigDecimal.valueOf(v).setScale(2, RoundingMode.HALF_UP); }

    static String sha256(String s) {
        try {
            return HexFormat.of().formatHex(MessageDigest.getInstance("SHA-256").digest(s.getBytes(StandardCharsets.UTF_8)));
        } catch (NoSuchAlgorithmException e) { throw new IllegalStateException(e); }
    }
}
