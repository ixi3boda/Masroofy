package com.masroofy.backend.service;

import com.masroofy.backend.dto.response.AccountResponse;
import com.masroofy.backend.repository.AccountRepository;
import java.time.Clock;
import java.util.List;
import java.util.UUID;
import org.springframework.stereotype.Service;

@Service
public class AccountService {

    private final AccountRepository accountRepository;
    private final Clock clock;

    public AccountService(AccountRepository accountRepository, Clock clock) {
        this.accountRepository = accountRepository;
        this.clock = clock;
    }

    /** Open accounts, oldest first; the first one is the app's default. */
    public List<AccountResponse> listAccounts(UUID userId) {
        return accountRepository.findOpenByUser(userId).stream().map(AccountResponse::from).toList();
    }

    /** Gives the user a "Cash" account unless they already have one. Returns true when it was created. */
    public boolean createDefaultCash(UUID userId) {
        return accountRepository.insertDefaultCash(UUID.randomUUID(), userId, clock.instant());
    }
}
