package com.financeapp.sms.ledger;

import com.financeapp.sms.domain.Account;
import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.domain.TxStatus;
import com.financeapp.sms.domain.TxType;
import java.math.BigDecimal;
import java.util.Objects;

/**
 * The only place that changes account balances. Every apply has exactly one matching reverse,
 * tracked by Transaction.applied, so edits, rejections and retries can never count a transaction twice.
 */
public final class Ledger {
    private Ledger() {}

    /** Signed change to the account balance. Money out: -(amount + fee). Money in: +(amount - fee). */
    public static BigDecimal delta(TxType type, BigDecimal amount, BigDecimal fee) {
        Objects.requireNonNull(amount, "amount");
        if (amount.signum() <= 0) throw new IllegalArgumentException("amount must be positive");
        BigDecimal f = fee == null ? BigDecimal.ZERO : fee;
        if (f.signum() < 0) throw new IllegalArgumentException("fee must not be negative");
        return switch (type) {
            case CREDIT, TRANSFER_IN -> amount.subtract(f);
            case DEBIT, TRANSFER_OUT, ATM_WITHDRAWAL, BILL_PAYMENT -> amount.add(f).negate();
            case OTHER -> throw new IllegalArgumentException("choose a transaction type before applying it");
        };
    }

    public static void apply(Account account, Transaction t) {
        if (t.isApplied()) throw new IllegalStateException("transaction " + t.getId() + " is already counted");
        if (!Objects.equals(account.getId(), t.getAccountId())) throw new IllegalArgumentException("account mismatch");
        if (!Objects.equals(account.getUserId(), t.getUserId())) throw new IllegalArgumentException("user mismatch");
        account.setBalance(account.getBalance().add(delta(t.getType(), t.getAmount(), t.getFee())));
        t.setApplied(true);
        t.setStatus(TxStatus.CONFIRMED);
    }

    public static void reverse(Account account, Transaction t) {
        if (!t.isApplied()) throw new IllegalStateException("transaction " + t.getId() + " is not counted");
        if (!Objects.equals(account.getId(), t.getAccountId())) throw new IllegalArgumentException("account mismatch");
        account.setBalance(account.getBalance().subtract(delta(t.getType(), t.getAmount(), t.getFee())));
        t.setApplied(false);
    }

    /**
     * For budgets and charts. Own-account transfers and ATM withdrawals move money between the user's
     * own accounts, so they are not spending (an ATM fee still is; track it via the fee field).
     */
    public static boolean countsAsSpending(Transaction t) {
        if (t.getStatus() != TxStatus.CONFIRMED || t.isInternalTransfer()) return false;
        return t.getType() == TxType.DEBIT || t.getType() == TxType.BILL_PAYMENT || t.getType() == TxType.TRANSFER_OUT;
    }
}
