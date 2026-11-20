package com.financeapp.sms.domain;

import java.util.Locale;

/** Transaction types, identical to the SMS model's labels. */
public enum TxType {
    DEBIT, CREDIT, TRANSFER_OUT, TRANSFER_IN, ATM_WITHDRAWAL, BILL_PAYMENT, OTHER;

    /** "debit" -> DEBIT, "atm_withdrawal" -> ATM_WITHDRAWAL; unknown values -> OTHER. */
    public static TxType fromLabel(String label) {
        if (label == null) return OTHER;
        try { return valueOf(label.trim().toUpperCase(Locale.ROOT)); }
        catch (IllegalArgumentException e) { return OTHER; }
    }
}
