package com.financeapp.sms.service;

import com.financeapp.sms.repo.AccountKey;
import com.financeapp.sms.repo.AccountRepository;
import java.util.List;
import java.util.Optional;
import org.springframework.stereotype.Service;

/**
 * Finds which of the user's accounts an SMS belongs to:
 *  1. same bank/app and same last 4 digits;
 *  2. otherwise, the only account of that bank/app that has no last-4 recorded (or the only one, if the SMS shows none).
 * No match -> the transaction becomes a draft and the user picks the account; that choice is remembered
 * (SmsReviewService copies the bank name and last 4 onto the account).
 */
@Service
public class AccountMatcher {
    private final AccountRepository accounts;

    public AccountMatcher(AccountRepository accounts) { this.accounts = accounts; }

    public Optional<AccountKey> match(Long userId, String institution, String last4) {
        if (institution == null) return Optional.empty();
        List<AccountKey> same = accounts.findKeysByUserId(userId).stream()
                .filter(a -> a.institution() != null && a.institution().equalsIgnoreCase(institution))
                .toList();
        if (last4 != null) {
            List<AccountKey> exact = same.stream().filter(a -> last4.equals(a.last4())).toList();
            if (exact.size() == 1) return Optional.of(exact.get(0));
            List<AccountKey> open = same.stream().filter(a -> a.last4() == null).toList();
            return open.size() == 1 ? Optional.of(open.get(0)) : Optional.empty();
        }
        return same.size() == 1 ? Optional.of(same.get(0)) : Optional.empty();
    }
}
