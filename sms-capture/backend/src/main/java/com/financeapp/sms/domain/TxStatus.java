package com.financeapp.sms.domain;

/** DRAFT = waiting for the user's review (balance untouched); CONFIRMED = counted in the balance; REJECTED = ignored. */
public enum TxStatus { DRAFT, CONFIRMED, REJECTED }
