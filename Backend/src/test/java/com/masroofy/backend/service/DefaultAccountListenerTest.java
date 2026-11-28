package com.masroofy.backend.service;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;

class DefaultAccountListenerTest {

    private final AccountService accountService = mock(AccountService.class);
    private final DefaultAccountListener listener = new DefaultAccountListener(accountService);

    @Test
    void givesTheNewUserACashAccount() {
        UUID id = UUID.randomUUID();

        listener.onUserRegistered(new UserRegisteredEvent(id, "new@example.com"));

        verify(accountService).createDefaultCash(id);
    }

    @Test
    void aFailureNeverReachesTheSignUp() {
        UUID id = UUID.randomUUID();
        when(accountService.createDefaultCash(id)).thenThrow(new DataAccessResourceFailureException("db down"));

        listener.onUserRegistered(new UserRegisteredEvent(id, "new@example.com"));   // no exception
    }
}
