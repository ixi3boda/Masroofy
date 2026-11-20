package com.financeapp.sms.parser;

import java.time.LocalDate;
import java.time.LocalTime;

/** Result of parsing one SMS. Field meanings follow the training dataset's "expected" object. */
public final class ParsedSms {
    public boolean isTransaction;
    /** debit, credit, transfer_out, transfer_in, atm_withdrawal, bill_payment, other; null if not a transaction. */
    public String type;
    public Double amount;
    /** ISO code (EGP, USD, ...) or null when the SMS shows no currency. */
    public String currency;
    public Double fee;
    public Double balanceAfter;
    /** Shop, person, biller or employer as written in the SMS. */
    public String merchant;
    /** card, instapay, wallet, bank_transfer, atm, other, unknown. */
    public String channel;
    public LocalDate date;
    /** Null when the SMS gives a date without a time. */
    public LocalTime time;
    public String accountLast4;
    /** Top probability of the transaction-type classifier (0..1). */
    public double confidence;
    /** Why a message was rejected after classification, e.g. "no amount found". */
    public String reason;

    /** Same format as the Python model: yyyy-MM-dd or yyyy-MM-ddTHH:mm:00, or null. */
    public String isoDateTime() {
        if (date == null) return null;
        if (time == null) return date.toString();
        return String.format("%sT%02d:%02d:00", date, time.getHour(), time.getMinute());
    }

    @Override public String toString() {
        return "ParsedSms{tx=" + isTransaction + ", type=" + type + ", amount=" + amount + ", currency=" + currency
                + ", fee=" + fee + ", balance=" + balanceAfter + ", merchant=" + merchant + ", channel=" + channel
                + ", datetime=" + isoDateTime() + ", last4=" + accountLast4 + ", confidence=" + confidence + "}";
    }
}
