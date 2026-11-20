package com.financeapp.sms.service;

import com.financeapp.sms.domain.Account;
import com.financeapp.sms.domain.SmsStatus;
import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.domain.TxStatus;
import com.financeapp.sms.domain.TxType;
import com.financeapp.sms.ledger.Ledger;
import com.financeapp.sms.repo.AccountRepository;
import com.financeapp.sms.repo.SmsMessageRepository;
import com.financeapp.sms.repo.TransactionRepository;
import java.math.BigDecimal;
import java.time.Instant;
import java.util.List;
import java.util.Objects;
import org.springframework.http.HttpStatus;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.server.ResponseStatusException;

/** The user's review of SMS transactions: confirm (optionally with corrections), edit, or reject. */
@Service
public class SmsReviewService {

    /** All fields optional: null = keep what the SMS said. */
    public record Edits(Long accountId, String type, BigDecimal amount, BigDecimal fee, String merchant,
                        Instant occurredAt, String category) {}

    private final TransactionRepository transactions;
    private final AccountRepository accounts;
    private final SmsMessageRepository messages;

    public SmsReviewService(TransactionRepository transactions, AccountRepository accounts, SmsMessageRepository messages) {
        this.transactions = transactions; this.accounts = accounts; this.messages = messages;
    }

    public List<Transaction> drafts(Long userId) {
        return transactions.findByUserIdAndStatusOrderByOccurredAtDesc(userId, TxStatus.DRAFT);
    }

    /** Confirms a draft, or corrects an already-confirmed transaction: reverse old effect, apply new one. */
    @Transactional
    public Transaction confirm(Long userId, Long txId, Edits e) {
        Transaction t = transactions.lockByIdAndUserId(txId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "transaction not found"));
        if (t.getStatus() == TxStatus.REJECTED) throw new ResponseStatusException(HttpStatus.CONFLICT, "transaction was rejected");

        // 1. Work out and validate the new values before touching any balance.
        TxType type = e != null && e.type() != null ? TxType.fromLabel(e.type()) : t.getType();
        BigDecimal amount = e != null && e.amount() != null ? e.amount() : t.getAmount();
        BigDecimal fee = e != null && e.fee() != null ? e.fee() : t.getFee();
        if (type == TxType.OTHER) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "choose a transaction type");
        if (amount == null || amount.signum() <= 0) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "amount must be positive");
        if (fee.signum() < 0) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "fee must not be negative");
        Long oldAccountId = t.isApplied() ? t.getAccountId() : null;
        Long newAccountId = e != null && e.accountId() != null ? e.accountId() : t.getAccountId();
        if (newAccountId == null) throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "choose an account");

        // 2. Lock the account rows, in id order so two concurrent edits can't deadlock.
        Account oldAcc = null, newAcc;
        if (oldAccountId != null && !oldAccountId.equals(newAccountId)) {
            Account a1 = lock(userId, Math.min(oldAccountId, newAccountId)), a2 = lock(userId, Math.max(oldAccountId, newAccountId));
            oldAcc = a1.getId().equals(oldAccountId) ? a1 : a2;
            newAcc = a1.getId().equals(newAccountId) ? a1 : a2;
        } else {
            newAcc = lock(userId, newAccountId);
            if (oldAccountId != null) oldAcc = newAcc;
        }
        String currency = t.getCurrency();
        if (!currency.equalsIgnoreCase(newAcc.getCurrency())) {
            // e.g. a USD purchase on an EGP card: the user must enter the amount actually charged in EGP.
            if (e == null || e.amount() == null) {
                throw new ResponseStatusException(HttpStatus.BAD_REQUEST, "enter the amount in " + newAcc.getCurrency());
            }
            currency = newAcc.getCurrency();
        }

        // 3. Undo the old effect (with the OLD values), update, apply the new effect.
        if (t.isApplied()) Ledger.reverse(oldAcc, t);
        t.setType(type);
        t.setAmount(amount);
        t.setFee(fee);
        t.setCurrency(currency);
        t.setAccountId(newAcc.getId());
        if (e != null) {
            if (e.merchant() != null) t.setMerchant(e.merchant().isBlank() ? null : e.merchant().trim());
            if (e.occurredAt() != null) t.setOccurredAt(e.occurredAt());
            if (e.category() != null) t.setCategory(e.category().isBlank() ? null : e.category().trim());
        }
        Ledger.apply(newAcc, t);
        t.setReviewReasons(null);
        t.setDuplicateOfId(null);
        // The bank's reported balance is only comparable when a transaction is applied as it arrives (see ingest);
        // by review time later transactions may already be counted, so drop the stale comparison.
        t.setBalanceDifference(null);

        // Remember the mapping so the next SMS from this bank/card matches automatically.
        if (newAcc.getInstitution() == null && t.getInstitution() != null) newAcc.setInstitution(t.getInstitution());
        if (newAcc.getLast4() == null && t.getAccountLast4() != null && Objects.equals(newAcc.getInstitution(), t.getInstitution())) {
            newAcc.setLast4(t.getAccountLast4());
        }
        setSmsStatus(t, SmsStatus.APPLIED);
        return transactions.save(t);
    }

    /** Rejects a draft, or removes a confirmed SMS transaction and gives the money back to the balance. */
    @Transactional
    public Transaction reject(Long userId, Long txId) {
        Transaction t = transactions.lockByIdAndUserId(txId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "transaction not found"));
        if (t.getStatus() == TxStatus.REJECTED) return t;
        if (t.isApplied()) Ledger.reverse(lock(userId, t.getAccountId()), t);
        t.setStatus(TxStatus.REJECTED);
        if (t.getTransferGroup() != null) {              // unlink the other half of an own-account transfer
            transactions.findNear(userId, t.getAmount(), TxStatus.REJECTED,
                            t.getOccurredAt().minusSeconds(86_400), t.getOccurredAt().plusSeconds(86_400)).stream()
                    .filter(o -> t.getTransferGroup().equals(o.getTransferGroup()) && !o.getId().equals(t.getId()))
                    .forEach(o -> { o.setTransferGroup(null); o.setInternalTransfer(false); transactions.save(o); });
            t.setTransferGroup(null);
            t.setInternalTransfer(false);
        }
        setSmsStatus(t, SmsStatus.IGNORED);
        return transactions.save(t);
    }

    private Account lock(Long userId, Long accountId) {
        return accounts.lockByIdAndUserId(accountId, userId)
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.BAD_REQUEST, "account not found"));
    }

    private void setSmsStatus(Transaction t, SmsStatus s) {
        if (t.getSmsMessageId() != null) messages.findById(t.getSmsMessageId()).ifPresent(m -> { m.setStatus(s); messages.save(m); });
    }
}
