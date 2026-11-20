package com.financeapp.sms.domain;

/** APPLIED = transaction created and counted; DRAFT = transaction created for review; IGNORED = not a transaction. */
public enum SmsStatus { APPLIED, DRAFT, IGNORED }
