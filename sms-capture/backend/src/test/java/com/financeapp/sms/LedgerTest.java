package com.financeapp.sms;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.financeapp.sms.domain.Account;
import com.financeapp.sms.domain.AccountType;
import com.financeapp.sms.domain.Transaction;
import com.financeapp.sms.domain.TxStatus;
import com.financeapp.sms.domain.TxType;
import com.financeapp.sms.ledger.Ledger;
import java.math.BigDecimal;
import java.time.Instant;
import org.junit.jupiter.api.Test;

class LedgerTest {

    private static Account account(String balance) {
        Account a = new Account(1L, "Card", AccountType.CARD, "NileBank", "6402", new BigDecimal(balance));
        a.setId(10L);
        return a;
    }

    private static Transaction tx(TxType type, String amount, String fee) {
        Transaction t = new Transaction();
        t.setUserId(1L); t.setAccountId(10L); t.setType(type);
        t.setAmount(new BigDecimal(amount)); t.setFee(new BigDecimal(fee)); t.setOccurredAt(Instant.now());
        return t;
    }

    @Test
    void moneyOutAndInWithFees() {
        assertEquals(new BigDecimal("-1257.50"), Ledger.delta(TxType.DEBIT, new BigDecimal("1250.00"), new BigDecimal("7.50")));
        assertEquals(new BigDecimal("-3010"), Ledger.delta(TxType.ATM_WITHDRAWAL, new BigDecimal("3000"), new BigDecimal("10")));
        assertEquals(new BigDecimal("499.50"), Ledger.delta(TxType.TRANSFER_IN, new BigDecimal("500.00"), new BigDecimal("0.50")));
        assertEquals(new BigDecimal("14350.00"), Ledger.delta(TxType.CREDIT, new BigDecimal("14350.00"), BigDecimal.ZERO));
    }

    @Test
    void applyThenReverseRestoresBalanceExactly() {
        Account a = account("10000.00");
        Transaction t = tx(TxType.BILL_PAYMENT, "189.00", "2.00");
        Ledger.apply(a, t);
        assertEquals(0, a.getBalance().compareTo(new BigDecimal("9809.00")), "after bill");
        assertTrue(t.isApplied(), "applied");
        assertEquals(TxStatus.CONFIRMED, t.getStatus());
        Ledger.reverse(a, t);
        assertEquals(0, a.getBalance().compareTo(new BigDecimal("10000.00")), "after reverse");
        assertFalse(t.isApplied(), "not applied");
    }

    @Test
    void cannotCountTwiceOrUseUnknownType() {
        Account a = account("100");
        Transaction t = tx(TxType.DEBIT, "10", "0");
        Ledger.apply(a, t);
        assertThrows(IllegalStateException.class, () -> Ledger.apply(a, t));
        assertThrows(IllegalArgumentException.class, () -> Ledger.apply(a, tx(TxType.OTHER, "10", "0")));
        assertThrows(IllegalArgumentException.class, () -> Ledger.delta(TxType.DEBIT, new BigDecimal("-1"), BigDecimal.ZERO));
    }

    @Test
    void ownTransfersAndAtmAreNotSpending() {
        Transaction out = tx(TxType.TRANSFER_OUT, "1000", "0");
        out.setStatus(TxStatus.CONFIRMED);
        assertTrue(Ledger.countsAsSpending(out), "transfer to someone else is spending");
        out.setInternalTransfer(true);
        assertFalse(Ledger.countsAsSpending(out), "transfer between own accounts is not");
        Transaction atm = tx(TxType.ATM_WITHDRAWAL, "500", "5");
        atm.setStatus(TxStatus.CONFIRMED);
        assertFalse(Ledger.countsAsSpending(atm), "cash withdrawal moves money to cash");
    }
}
