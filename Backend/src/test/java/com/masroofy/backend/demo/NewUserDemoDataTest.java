package com.masroofy.backend.demo;

import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import com.masroofy.backend.service.UserRegisteredEvent;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.springframework.dao.DataAccessResourceFailureException;

class NewUserDemoDataTest {

    private final DemoLedgerLoader loader = mock(DemoLedgerLoader.class);
    private final NewUserDemoData listener = new NewUserDemoData(loader);

    @Test
    void loadsDemoDataForTheNewUser() {
        UUID id = UUID.randomUUID();

        listener.onUserRegistered(new UserRegisteredEvent(id, "new@example.com"));

        verify(loader).load(id);
    }

    @Test
    void aFailureNeverReachesTheSignUp() {
        UUID id = UUID.randomUUID();
        when(loader.load(id)).thenThrow(new DataAccessResourceFailureException("db down"));

        listener.onUserRegistered(new UserRegisteredEvent(id, "new@example.com"));   // no exception
    }
}
