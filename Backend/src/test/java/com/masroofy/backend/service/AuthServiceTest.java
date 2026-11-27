package com.masroofy.backend.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.Mockito.doThrow;
import static org.mockito.Mockito.inOrder;
import static org.mockito.Mockito.lenient;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;
import static org.mockito.Mockito.when;

import com.masroofy.backend.dto.request.EmailRequest;
import com.masroofy.backend.dto.request.LoginRequest;
import com.masroofy.backend.dto.request.RefreshTokenRequest;
import com.masroofy.backend.dto.request.RegisterRequest;
import com.masroofy.backend.dto.request.ResetPasswordRequest;
import com.masroofy.backend.dto.request.VerifyCodeRequest;
import com.masroofy.backend.dto.response.AuthTokensResponse;
import com.masroofy.backend.dto.response.CodeDispatchResponse;
import com.masroofy.backend.dto.response.RegisterResponse;
import com.masroofy.backend.dto.response.ResetCodeVerifiedResponse;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.FirebaseSession;
import com.masroofy.backend.model.AuthCode;
import com.masroofy.backend.model.AuthCodePurpose;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.util.SecureCodes;
import com.masroofy.backend.service.AuthCodeService.IssuedCode;
import com.masroofy.backend.service.AuthCodeService.IssuedToken;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.time.ZoneOffset;
import java.util.Optional;
import java.util.UUID;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Nested;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.ArgumentCaptor;
import org.mockito.InOrder;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import org.springframework.dao.DataAccessResourceFailureException;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.transaction.PlatformTransactionManager;
import org.springframework.transaction.support.TransactionTemplate;

@ExtendWith(MockitoExtension.class)
class AuthServiceTest {

    private static final Instant NOW = Instant.parse("2026-11-19T10:00:00Z");
    private static final String EMAIL = "mariam@example.com";
    private static final String UID = "firebase-uid-1";
    private static final String GOOD_PASSWORD = "Sunny-Nile9";

    @Mock
    private UserRepository userRepository;
    @Mock
    private AuthCodeService authCodeService;
    @Mock
    private FirebaseIdentityClient firebase;
    @Mock
    private EmailService emailService;

    private AuthService service;
    private final RefreshTokenSeal seal = new RefreshTokenSeal(
            new SecureCodes("test-secret-test-secret-test-secret-123", new java.security.SecureRandom()));

    @BeforeEach
    void setUp() {
        TransactionTemplate tx = new TransactionTemplate(mock(PlatformTransactionManager.class));
        service = new AuthService(userRepository, authCodeService, firebase, emailService, new PasswordPolicy(), tx,
                Clock.fixed(NOW, ZoneOffset.UTC), seal);
        service.rollbackBackoff = Duration.ZERO;
        lenient().when(authCodeService.codeLength()).thenReturn(6);
        lenient().when(authCodeService.codeTtlSeconds()).thenReturn(600L);
        lenient().when(authCodeService.resendCooldownSeconds()).thenReturn(60L);
        lenient().when(authCodeService.secondsUntil(any())).thenReturn(600L);
    }

    private static User user(boolean verified) {
        return new User(UUID.fromString("22222222-2222-2222-2222-222222222222"), UID, EMAIL, null, "Mariam Ali",
                "EGP", "en", "Africa/Cairo", null, verified ? NOW.minusSeconds(3600) : null,
                NOW.minusSeconds(7200), NOW.minusSeconds(7200), NOW.minusSeconds(7200));
    }

    private static FirebaseSession session() {
        return new FirebaseSession("id-token", "refresh-token", 3600, UID);
    }

    private static void assertError(Runnable call, ErrorCode expected) {
        assertThatThrownBy(call::run)
                .isInstanceOfSatisfying(ApiException.class, e -> assertThat(e.getErrorCode()).isEqualTo(expected));
    }

    @Nested
    class Register {

        private final RegisterRequest request =
                new RegisterRequest("  Mariam   Ali ", " Mariam@Example.com ", GOOD_PASSWORD, true);

        @Test
        void createsFirebaseUserProfileAndSendsVerificationCode() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(EMAIL, GOOD_PASSWORD, "Mariam Ali")).thenReturn(UID);
            when(authCodeService.issueCode(any(), eq(AuthCodePurpose.EMAIL_VERIFICATION)))
                    .thenReturn(new IssuedCode("042517", NOW.plusSeconds(600)));

            RegisterResponse response = service.register(request);

            ArgumentCaptor<User> saved = ArgumentCaptor.forClass(User.class);
            verify(userRepository).insert(saved.capture());
            User user = saved.getValue();
            assertThat(user.firebaseUid()).isEqualTo(UID);
            assertThat(user.email()).isEqualTo(EMAIL);
            assertThat(user.fullName()).isEqualTo("Mariam Ali");
            assertThat(user.baseCurrency()).isEqualTo("EGP");
            assertThat(user.locale()).isEqualTo("en");
            assertThat(user.timezone()).isEqualTo("Africa/Cairo");
            assertThat(user.emailVerifiedAt()).isNull();
            assertThat(user.termsAcceptedAt()).isEqualTo(NOW);

            verify(emailService).sendVerificationCode(EMAIL, "Mariam Ali", "042517", Duration.ofSeconds(600));
            assertThat(response.verificationEmailSent()).isTrue();
            assertThat(response.user().emailVerified()).isFalse();
            assertThat(response.user().id()).isEqualTo(user.id());
            assertThat(response.verification().maskedEmail()).isEqualTo("m***@example.com");
            assertThat(response.verification().codeLength()).isEqualTo(6);
            assertThat(response.verification().resendAvailableInSeconds()).isEqualTo(60);
        }

        @Test
        void rejectsWeakPasswordBeforeTouchingFirebase() {
            RegisterRequest weak = new RegisterRequest("Mariam Ali", EMAIL, "mariam123", true);

            assertError(() -> service.register(weak), ErrorCode.WEAK_PASSWORD);
            verifyNoInteractions(firebase);
        }

        @Test
        void announcesTheNewUserOnlyAfterASuccessfulSignUp() {
            java.util.List<Object> events = new java.util.ArrayList<>();
            service.setEventPublisher(events::add);
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(EMAIL, GOOD_PASSWORD, "Mariam Ali")).thenReturn(UID);
            when(authCodeService.issueCode(any(), eq(AuthCodePurpose.EMAIL_VERIFICATION)))
                    .thenReturn(new IssuedCode("042517", NOW.plusSeconds(600)));

            RegisterResponse response = service.register(request);

            assertThat(events).containsExactly(
                    new com.masroofy.backend.service.UserRegisteredEvent(response.user().id(), EMAIL));

            events.clear();
            when(userRepository.existsByEmail(EMAIL)).thenReturn(true);
            assertError(() -> service.register(request), ErrorCode.EMAIL_ALREADY_IN_USE);
            assertThat(events).isEmpty();
        }

        @Test
        void rejectsDuplicateEmail() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(true);

            assertError(() -> service.register(request), ErrorCode.EMAIL_ALREADY_IN_USE);
            verifyNoInteractions(firebase);
        }

        @Test
        void deletesFirebaseUserWhenDatabaseInsertFails() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(anyString(), anyString(), anyString())).thenReturn(UID);
            doThrow(new DataAccessResourceFailureException("db down")).when(userRepository).insert(any());

            assertThatThrownBy(() -> service.register(request)).isInstanceOf(DataAccessResourceFailureException.class);
            verify(firebase).deleteUser(UID);
            verifyNoInteractions(emailService);
        }

        @Test
        void concurrentDuplicateBecomesEmailAlreadyInUse() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(anyString(), anyString(), anyString())).thenReturn(UID);
            doThrow(new DuplicateKeyException("uk_users_email")).when(userRepository).insert(any());

            assertError(() -> service.register(request), ErrorCode.EMAIL_ALREADY_IN_USE);
            verify(firebase).deleteUser(UID);
        }

        @Test
        void signUpIsSerializedPerEmailBeforeFirebaseIsCalled() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(EMAIL, GOOD_PASSWORD, "Mariam Ali")).thenReturn(UID);
            when(authCodeService.issueCode(any(), any())).thenReturn(new IssuedCode("042517", NOW.plusSeconds(600)));

            service.register(request);

            InOrder order = inOrder(userRepository, firebase, authCodeService);
            order.verify(userRepository).lockEmail(EMAIL);
            order.verify(userRepository).existsByEmail(EMAIL);
            order.verify(firebase).createUser(EMAIL, GOOD_PASSWORD, "Mariam Ali");
            order.verify(userRepository).insert(any());
            order.verify(authCodeService).recordDispatch(EMAIL, AuthCodePurpose.EMAIL_VERIFICATION);
            order.verify(authCodeService).issueCode(any(), eq(AuthCodePurpose.EMAIL_VERIFICATION));
        }

        @Test
        void firebaseCleanupIsRetriedUntilItWorks() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(anyString(), anyString(), anyString())).thenReturn(UID);
            doThrow(new DuplicateKeyException("uk_users_firebase_uid")).when(userRepository).insert(any());
            doThrow(new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE))
                    .doThrow(new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE))
                    .doNothing()
                    .when(firebase).deleteUser(UID);

            assertError(() -> service.register(request), ErrorCode.EMAIL_ALREADY_IN_USE);
            verify(firebase, org.mockito.Mockito.times(3)).deleteUser(UID);
        }

        @Test
        void emailTakenInFirebaseOnlyDeletesNothing() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(anyString(), anyString(), anyString()))
                    .thenThrow(new ApiException(ErrorCode.EMAIL_ALREADY_IN_USE));

            assertError(() -> service.register(request), ErrorCode.EMAIL_ALREADY_IN_USE);
            verify(firebase, never()).deleteUser(any());
            verify(userRepository, never()).insert(any());
        }

        @Test
        void accountIsStillCreatedWhenEmailFails() {
            when(userRepository.existsByEmail(EMAIL)).thenReturn(false);
            when(firebase.createUser(anyString(), anyString(), anyString())).thenReturn(UID);
            when(authCodeService.issueCode(any(), any())).thenReturn(new IssuedCode("042517", NOW.plusSeconds(600)));
            doThrow(new ApiException(ErrorCode.EMAIL_DELIVERY_FAILED))
                    .when(emailService).sendVerificationCode(anyString(), anyString(), anyString(), any());

            RegisterResponse response = service.register(request);

            assertThat(response.verificationEmailSent()).isFalse();
            verify(firebase, never()).deleteUser(any());
        }
    }

    @Nested
    class VerifyEmail {

        @Test
        void verifiesCodeAndMarksUserVerifiedInDatabaseAndFirebase() {
            User user = user(false);
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user));

            var response = service.verifyEmail(new VerifyCodeRequest("MARIAM@example.com", "042517"));

            assertThat(response.emailVerified()).isTrue();
            InOrder order = inOrder(authCodeService, userRepository, firebase);
            order.verify(authCodeService).verifyCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION, "042517");
            order.verify(userRepository).markEmailVerified(user.id(), NOW);
            order.verify(firebase).markEmailVerified(UID);
        }

        @Test
        void firebaseFailureDoesNotUndoVerification() {
            User user = user(false);
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user));
            doThrow(new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE)).when(firebase).markEmailVerified(UID);

            assertThat(service.verifyEmail(new VerifyCodeRequest(EMAIL, "042517")).emailVerified()).isTrue();
            verify(userRepository).markEmailVerified(user.id(), NOW);
        }

        @Test
        void unknownEmailLooksLikeAWrongCode() {
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.empty());

            assertError(() -> service.verifyEmail(new VerifyCodeRequest(EMAIL, "042517")),
                    ErrorCode.INVALID_OR_EXPIRED_CODE);
        }

        @Test
        void alreadyVerifiedEmailIsReported() {
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user(true)));

            assertError(() -> service.verifyEmail(new VerifyCodeRequest(EMAIL, "042517")),
                    ErrorCode.EMAIL_ALREADY_VERIFIED);
            verifyNoInteractions(authCodeService);
        }

        @Test
        void wrongCodeLeavesUserUnverified() {
            User user = user(false);
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user));
            doThrow(new ApiException(ErrorCode.INVALID_CODE))
                    .when(authCodeService).verifyCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION, "000000");

            assertError(() -> service.verifyEmail(new VerifyCodeRequest(EMAIL, "000000")), ErrorCode.INVALID_CODE);
            verify(userRepository, never()).markEmailVerified(any(), any());
        }

        @Test
        void resendCooldownIsCheckedBeforeTheLookupSoUnknownEmailsAnswerTheSame() {
            doThrow(new ApiException(ErrorCode.RESEND_COOLDOWN)).when(authCodeService)
                    .reserveDispatch("nobody@example.com", AuthCodePurpose.EMAIL_VERIFICATION);

            assertError(() -> service.resendVerificationCode(new EmailRequest("Nobody@Example.com")),
                    ErrorCode.RESEND_COOLDOWN);
            verify(userRepository, never()).findByEmail(any());
        }

        @Test
        void resendSendsANewCode() {
            User user = user(false);
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user));
            when(authCodeService.issueCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION))
                    .thenReturn(new IssuedCode("777777", NOW.plusSeconds(600)));

            CodeDispatchResponse response = service.resendVerificationCode(new EmailRequest(EMAIL));

            verify(emailService).sendVerificationCode(EMAIL, "Mariam Ali", "777777", Duration.ofSeconds(600));
            assertThat(response.maskedEmail()).isEqualTo("m***@example.com");
        }

        @Test
        void resendForUnknownOrVerifiedEmailSendsNothingButLooksTheSame() {
            when(userRepository.findByEmail("ghost@example.com")).thenReturn(Optional.empty());
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user(true)));

            CodeDispatchResponse unknown = service.resendVerificationCode(new EmailRequest("ghost@example.com"));
            CodeDispatchResponse verified = service.resendVerificationCode(new EmailRequest(EMAIL));

            assertThat(unknown.maskedEmail()).isEqualTo("g***@example.com");
            assertThat(unknown.codeLength()).isEqualTo(verified.codeLength()).isEqualTo(6);
            verifyNoInteractions(emailService);
            verify(authCodeService, never()).issueCode(any(), any());
        }
    }

    @Nested
    class Login {

        @Test
        void returnsFirebaseTokensAndProfileForVerifiedUser() {
            when(firebase.signInWithPassword(EMAIL, GOOD_PASSWORD)).thenReturn(session());
            when(userRepository.findByFirebaseUid(UID)).thenReturn(Optional.of(user(true)));

            AuthTokensResponse response = service.login(new LoginRequest(" Mariam@Example.com", GOOD_PASSWORD));

            assertThat(response.accessToken()).isEqualTo("id-token");
            assertThat(seal.unseal(response.refreshToken()))
                    .contains(new RefreshTokenSeal.Unsealed(0, "refresh-token"));
            assertThat(response.tokenType()).isEqualTo("Bearer");
            assertThat(response.expiresIn()).isEqualTo(3600);
            assertThat(response.user().email()).isEqualTo(EMAIL);
            assertThat(response.user().emailVerified()).isTrue();
        }

        @Test
        void unverifiedUserGetsEmailNotVerifiedWithMaskedEmail() {
            when(firebase.signInWithPassword(EMAIL, GOOD_PASSWORD)).thenReturn(session());
            when(userRepository.findByFirebaseUid(UID)).thenReturn(Optional.of(user(false)));

            assertThatThrownBy(() -> service.login(new LoginRequest(EMAIL, GOOD_PASSWORD)))
                    .isInstanceOfSatisfying(ApiException.class, e -> {
                        assertThat(e.getErrorCode()).isEqualTo(ErrorCode.EMAIL_NOT_VERIFIED);
                        assertThat(e.getDetails()).containsEntry("maskedEmail", "m***@example.com");
                    });
        }

        @Test
        void wrongPasswordPropagatesInvalidCredentials() {
            when(firebase.signInWithPassword(EMAIL, "wrong"))
                    .thenThrow(new ApiException(ErrorCode.INVALID_CREDENTIALS));

            assertError(() -> service.login(new LoginRequest(EMAIL, "wrong")), ErrorCode.INVALID_CREDENTIALS);
        }

        @Test
        void firebaseUserWithoutProfileCannotLogIn() {
            when(firebase.signInWithPassword(EMAIL, GOOD_PASSWORD)).thenReturn(session());
            when(userRepository.findByFirebaseUid(UID)).thenReturn(Optional.empty());

            assertError(() -> service.login(new LoginRequest(EMAIL, GOOD_PASSWORD)), ErrorCode.INVALID_CREDENTIALS);
        }

        @Test
        void refreshReturnsNewTokens() {
            when(firebase.refreshSession("refresh-token")).thenReturn(session());
            when(userRepository.findByFirebaseUid(UID)).thenReturn(Optional.of(user(true)));

            AuthTokensResponse response = service.refresh(new RefreshTokenRequest(seal.seal(0, "refresh-token")));

            assertThat(response.accessToken()).isEqualTo("id-token");
            assertThat(seal.unseal(response.refreshToken())).contains(new RefreshTokenSeal.Unsealed(0, "refresh-token"));
        }

        @Test
        void refreshForDeletedProfileIsRejected() {
            when(firebase.refreshSession("refresh-token")).thenReturn(session());
            when(userRepository.findByFirebaseUid(UID)).thenReturn(Optional.empty());

            assertError(() -> service.refresh(new RefreshTokenRequest(seal.seal(0, "refresh-token"))),
                    ErrorCode.INVALID_REFRESH_TOKEN);
        }

        @Test
        void refreshTokenIssuedBeforeLastLogoutIsRejected() {
            User user = new User(user(true).id(), UID, EMAIL, null, "Mariam Ali", "EGP", "en", "Africa/Cairo", null,
                    NOW, NOW, NOW, NOW, 2);
            when(firebase.refreshSession("refresh-token")).thenReturn(session());
            when(userRepository.findByFirebaseUid(UID)).thenReturn(Optional.of(user));

            assertError(() -> service.refresh(new RefreshTokenRequest(seal.seal(1, "refresh-token"))),
                    ErrorCode.INVALID_REFRESH_TOKEN);
        }

        @Test
        void unsealedOrTamperedRefreshTokenNeverReachesFirebase() {
            String sealed = seal.seal(0, "refresh-token");
            for (String bad : new String[] {"refresh-token", "5" + sealed.substring(1), sealed + "x"}) {
                assertError(() -> service.refresh(new RefreshTokenRequest(bad)), ErrorCode.INVALID_REFRESH_TOKEN);
            }
            verifyNoInteractions(firebase);
        }

        @Test
        void logoutRaisesSessionVersionAndRevokesRefreshTokens() {
            User user = user(true);
            when(userRepository.findById(user.id())).thenReturn(Optional.of(user));

            service.logout(user.id());

            InOrder order = inOrder(firebase, userRepository);
            order.verify(firebase).setSessionVersion(UID, 1);
            order.verify(firebase).revokeRefreshTokens(UID);
            order.verify(userRepository).raiseSessionVersion(user.id(), 1);
        }

        @Test
        void logoutChangesNothingWhenFirebaseIsUnavailable() {
            User user = user(true);
            when(userRepository.findById(user.id())).thenReturn(Optional.of(user));
            doThrow(new ApiException(ErrorCode.AUTH_PROVIDER_UNAVAILABLE)).when(firebase).setSessionVersion(UID, 1);

            assertError(() -> service.logout(user.id()), ErrorCode.AUTH_PROVIDER_UNAVAILABLE);
            verify(firebase, never()).revokeRefreshTokens(anyString());
            verify(userRepository, never()).raiseSessionVersion(any(), eq(1));
        }

        @Test
        void logoutForDeletedProfileIsUnauthorized() {
            UUID id = UUID.randomUUID();
            when(userRepository.findById(id)).thenReturn(Optional.empty());

            assertError(() -> service.logout(id), ErrorCode.UNAUTHORIZED);
            verifyNoInteractions(firebase);
        }
    }

    @Nested
    class PasswordReset {

        private final AuthCode resetToken = new AuthCode(UUID.randomUUID(), user(true).id(),
                AuthCodePurpose.PASSWORD_RESET_TOKEN, "hash", 0, NOW.plusSeconds(900), null, NOW);

        @Test
        void forgotPasswordEmailsResetCode() {
            User user = user(true);
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user));
            when(authCodeService.issueCode(user.id(), AuthCodePurpose.PASSWORD_RESET))
                    .thenReturn(new IssuedCode("123456", NOW.plusSeconds(600)));

            CodeDispatchResponse response = service.forgotPassword(new EmailRequest(EMAIL));

            verify(emailService).sendPasswordResetCode(EMAIL, "Mariam Ali", "123456", Duration.ofSeconds(600));
            assertThat(response.maskedEmail()).isEqualTo("m***@example.com");
        }

        @Test
        void forgotPasswordForUnknownEmailRevealsNothing() {
            when(userRepository.findByEmail("ghost@example.com")).thenReturn(Optional.empty());

            CodeDispatchResponse response = service.forgotPassword(new EmailRequest("ghost@example.com"));

            assertThat(response.maskedEmail()).isEqualTo("g***@example.com");
            verifyNoInteractions(emailService);
        }

        @Test
        void verifyResetCodeReturnsResetToken() {
            User user = user(true);
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.of(user));
            when(authCodeService.issueResetToken(user.id()))
                    .thenReturn(new IssuedToken("reset-token", NOW.plusSeconds(900)));
            when(authCodeService.secondsUntil(NOW.plusSeconds(900))).thenReturn(900L);

            ResetCodeVerifiedResponse response = service.verifyResetCode(new VerifyCodeRequest(EMAIL, "123456"));

            verify(authCodeService).verifyCode(user.id(), AuthCodePurpose.PASSWORD_RESET, "123456");
            assertThat(response.resetToken()).isEqualTo("reset-token");
            assertThat(response.expiresInSeconds()).isEqualTo(900);
        }

        @Test
        void forgotCooldownIsCheckedBeforeTheLookupSoUnknownEmailsAnswerTheSame() {
            doThrow(new ApiException(ErrorCode.RESEND_COOLDOWN)).when(authCodeService)
                    .reserveDispatch("nobody@example.com", AuthCodePurpose.PASSWORD_RESET);

            assertError(() -> service.forgotPassword(new EmailRequest("nobody@example.com")),
                    ErrorCode.RESEND_COOLDOWN);
            verify(userRepository, never()).findByEmail(any());
        }

        @Test
        void verifyResetCodeForUnknownEmailLooksLikeWrongCode() {
            when(userRepository.findByEmail(EMAIL)).thenReturn(Optional.empty());

            assertError(() -> service.verifyResetCode(new VerifyCodeRequest(EMAIL, "123456")),
                    ErrorCode.INVALID_OR_EXPIRED_CODE);
        }

        @Test
        void resetUpdatesPasswordConsumesTokenAndSignsOutEverywhere() {
            User user = user(true);
            when(authCodeService.findActiveResetToken("reset-token")).thenReturn(resetToken);
            when(userRepository.findById(user.id())).thenReturn(Optional.of(user));
            when(firebase.signInWithPassword(EMAIL, "Fresh-Start7"))
                    .thenThrow(new ApiException(ErrorCode.INVALID_CREDENTIALS));

            var response = service.resetPassword(
                    new ResetPasswordRequest("reset-token", "Fresh-Start7", "Fresh-Start7"));

            assertThat(response.message()).contains("reset successfully");
            InOrder order = inOrder(firebase, authCodeService, userRepository);
            order.verify(firebase).updatePassword(UID, "Fresh-Start7");
            order.verify(authCodeService).consume(resetToken);
            order.verify(firebase).setSessionVersion(UID, 1);
            order.verify(firebase).revokeRefreshTokens(UID);
            order.verify(userRepository).raiseSessionVersion(user.id(), 1);
            verify(userRepository, never()).markEmailVerified(any(), any());
        }

        @Test
        void resetAlsoVerifiesAnUnverifiedEmail() {
            User user = user(false);
            when(authCodeService.findActiveResetToken("reset-token")).thenReturn(resetToken);
            when(userRepository.findById(user.id())).thenReturn(Optional.of(user));
            when(firebase.signInWithPassword(EMAIL, "Fresh-Start7"))
                    .thenThrow(new ApiException(ErrorCode.INVALID_CREDENTIALS));

            service.resetPassword(new ResetPasswordRequest("reset-token", "Fresh-Start7", "Fresh-Start7"));

            verify(userRepository).markEmailVerified(user.id(), NOW);
            verify(firebase).markEmailVerified(UID);
        }

        @Test
        void mismatchedPasswordsAreRejectedFirst() {
            assertThatThrownBy(() -> service.resetPassword(
                    new ResetPasswordRequest("reset-token", "Fresh-Start7", "Fresh-Start8")))
                    .isInstanceOfSatisfying(ApiException.class, e -> {
                        assertThat(e.getErrorCode()).isEqualTo(ErrorCode.PASSWORDS_DO_NOT_MATCH);
                        assertThat(e.getFieldErrors()).extracting("field").containsExactly("confirmPassword");
                    });
            verifyNoInteractions(authCodeService, firebase);
        }

        @Test
        void weakPasswordDoesNotConsumeTheToken() {
            User user = user(true);
            when(authCodeService.findActiveResetToken("reset-token")).thenReturn(resetToken);
            when(userRepository.findById(user.id())).thenReturn(Optional.of(user));

            assertError(() -> service.resetPassword(new ResetPasswordRequest("reset-token", "mariam99", "mariam99")),
                    ErrorCode.WEAK_PASSWORD);
            verify(authCodeService, never()).consume(any());
            verifyNoInteractions(firebase);
        }

        @Test
        void currentPasswordCannotBeReused() {
            User user = user(true);
            when(authCodeService.findActiveResetToken("reset-token")).thenReturn(resetToken);
            when(userRepository.findById(user.id())).thenReturn(Optional.of(user));
            when(firebase.signInWithPassword(EMAIL, "Same-Old-7")).thenReturn(session());

            assertError(() -> service.resetPassword(
                    new ResetPasswordRequest("reset-token", "Same-Old-7", "Same-Old-7")), ErrorCode.PASSWORD_REUSED);
            verify(firebase, never()).updatePassword(any(), any());
            verify(authCodeService, never()).consume(any());
        }

        @Test
        void providerErrorDuringReuseCheckIsNotSwallowed() {
            User user = user(true);
            when(authCodeService.findActiveResetToken("reset-token")).thenReturn(resetToken);
            when(userRepository.findById(user.id())).thenReturn(Optional.of(user));
            when(firebase.signInWithPassword(EMAIL, "Fresh-Start7"))
                    .thenThrow(new ApiException(ErrorCode.RATE_LIMITED));

            assertError(() -> service.resetPassword(
                    new ResetPasswordRequest("reset-token", "Fresh-Start7", "Fresh-Start7")), ErrorCode.RATE_LIMITED);
            verify(firebase, never()).updatePassword(any(), any());
        }

        @Test
        void invalidTokenIsRejected() {
            when(authCodeService.findActiveResetToken("bad"))
                    .thenThrow(new ApiException(ErrorCode.INVALID_RESET_TOKEN));

            assertError(() -> service.resetPassword(new ResetPasswordRequest("bad", "Fresh-Start7", "Fresh-Start7")),
                    ErrorCode.INVALID_RESET_TOKEN);
        }
    }
}
