package com.financeapp.sms.repo;

/** Lightweight account row used for matching; not a managed entity, so a later lock reads fresh data. */
public record AccountKey(Long id, String institution, String last4, String currency) {}
