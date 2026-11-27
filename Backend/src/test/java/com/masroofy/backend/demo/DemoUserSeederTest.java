package com.masroofy.backend.demo;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.masroofy.backend.config.DemoProperties;
import com.masroofy.backend.config.DemoProperties.DemoUser;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.FirebaseSession;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.PasswordPolicy;
import java.time.Clock;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;

@ExtendWith(MockitoExtension.class)
class DemoUserSeederTest {

    private static final Instant NOW = Instant.parse("2026-11-26T10:00:00Z");
    private static final DemoUser MARIAM = new DemoUser(" Mariam.Demo@Masroofy.app ", "Test-Lagoon-31", "Mariam Ali");

    @Mock
    private FirebaseIdentityClient firebase;
    @Mock
    private UserRepository userRepository;
    @Mock
    private DemoLedgerLoader ledgerLoader;

    private DemoUserSeeder seeder(DemoUser... users) {
        return new DemoUserSeeder(new DemoProperties(true, false, List.of(users)), firebase, userRepository,
                new PasswordPolicy(), ledgerLoader, Clock.fixed(NOW, ZoneOffset.UTC));
    }

    private static User dbUser(String uid, boolean verified) {
        return new User(UUID.randomUUID(), uid, "mariam.demo@masroofy.app", null, "Mariam Ali", "EGP", "en",
                "Africa/Cairo", null, verified ? NOW : null, NOW, NOW, NOW);
    }

    @Test
    void createsTheUserInFirebaseAndPostgresThenLoadsDemoData() {
        when(firebase.findUidByEmail("mariam.demo@masroofy.app")).thenReturn(Optional.empty());
        when(firebase.createUser("mariam.demo@masroofy.app", "Test-Lagoon-31", "Mariam Ali")).thenReturn("uid-new");
        when(userRepository.findByEmail("mariam.demo@masroofy.app")).thenReturn(Optional.empty());

        User user = seeder(MARIAM).seed(MARIAM);

        verify(firebase).markEmailVerified("uid-new");
        ArgumentCaptor<User> inserted = ArgumentCaptor.forClass(User.class);
        verify(userRepository).insert(inserted.capture());
        assertThat(inserted.getValue().firebaseUid()).isEqualTo("uid-new");
        assertThat(inserted.getValue().email()).isEqualTo("mariam.demo@masroofy.app");
        assertThat(inserted.getValue().isEmailVerified()).isTrue();
        assertThat(inserted.getValue().baseCurrency()).isEqualTo("EGP");
        assertThat(inserted.getValue().timezone()).isEqualTo("Africa/Cairo");
        verify(ledgerLoader).load(user.id());
        verify(firebase, never()).updatePassword(any(), any());
    }

    @Test
    void existingFirebaseUserWithTheRightPasswordIsLeftSignedIn() {
        User existing = dbUser("uid-1", true);
        when(firebase.findUidByEmail("mariam.demo@masroofy.app")).thenReturn(Optional.of("uid-1"));
        when(firebase.signInWithPassword("mariam.demo@masroofy.app", "Test-Lagoon-31"))
                .thenReturn(new FirebaseSession("id", "rt", 3600, "uid-1"));
        when(userRepository.findByEmail("mariam.demo@masroofy.app")).thenReturn(Optional.of(existing));

        seeder(MARIAM).seed(MARIAM);

        verify(firebase, never()).createUser(anyString(), anyString(), anyString());
        verify(firebase, never()).updatePassword(any(), any());
        verify(userRepository, never()).insert(any());
        verify(userRepository, never()).relinkFirebaseUid(any(), any(), any());
        verify(ledgerLoader).load(existing.id());
    }

    @Test
    void wrongFirebasePasswordIsResetToTheConfiguredOne() {
        when(firebase.findUidByEmail(anyString())).thenReturn(Optional.of("uid-1"));
        when(firebase.signInWithPassword(anyString(), anyString()))
                .thenThrow(new ApiException(ErrorCode.INVALID_CREDENTIALS));
        when(userRepository.findByEmail(anyString())).thenReturn(Optional.of(dbUser("uid-1", true)));

        seeder(MARIAM).seed(MARIAM);

        verify(firebase).updatePassword("uid-1", "Test-Lagoon-31");
    }

    @Test
    void databaseProfileIsRelinkedToARecreatedFirebaseAccountAndVerified() {
        User stale = dbUser("uid-old", false);
        when(firebase.findUidByEmail(anyString())).thenReturn(Optional.empty());
        when(firebase.createUser(anyString(), anyString(), anyString())).thenReturn("uid-new");
        when(userRepository.findByEmail(anyString())).thenReturn(Optional.of(stale));

        seeder(MARIAM).seed(MARIAM);

        verify(userRepository).relinkFirebaseUid(stale.id(), "uid-new", NOW);
        verify(userRepository).markEmailVerified(stale.id(), NOW);
        verify(userRepository, never()).insert(any());
    }

    @Test
    void weakOrMissingPasswordsAreRefusedBeforeTouchingFirebase() {
        DemoUser weak = new DemoUser("mariam.demo@masroofy.app", "mariam123", "Mariam Ali");
        DemoUser none = new DemoUser("mariam.demo@masroofy.app", "", "Mariam Ali");

        assertThatThrownBy(() -> seeder(weak).seed(weak)).isInstanceOfSatisfying(ApiException.class,
                e -> assertThat(e.getErrorCode()).isEqualTo(ErrorCode.WEAK_PASSWORD));
        assertThatThrownBy(() -> seeder(none).seed(none)).isInstanceOf(IllegalStateException.class);
        verifyNoInteractions(firebase, ledgerLoader);
    }

    @Test
    void oneFailingDemoUserDoesNotStopTheOthersOrTheStartup() throws Exception {
        DemoUser omar = new DemoUser("omar.demo@masroofy.app", "Test-Cedar-58", "Omar Hassan");
        DemoUser blank = new DemoUser("", "x", "Nobody");
        DemoUser noPassword = new DemoUser("nopass.demo@masroofy.app", "", "No Password");
        when(firebase.findUidByEmail("mariam.demo@masroofy.app"))
                .thenThrow(new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE));
        when(firebase.findUidByEmail("omar.demo@masroofy.app")).thenReturn(Optional.empty());
        when(firebase.createUser("omar.demo@masroofy.app", "Test-Cedar-58", "Omar Hassan")).thenReturn("uid-omar");
        when(userRepository.findByEmail("omar.demo@masroofy.app")).thenReturn(Optional.empty());

        seeder(MARIAM, blank, noPassword, omar).run(null);

        verify(firebase, never()).findUidByEmail("nopass.demo@masroofy.app");

        verify(firebase).createUser("omar.demo@masroofy.app", "Test-Cedar-58", "Omar Hassan");
        verify(ledgerLoader).load(any());
    }
}
