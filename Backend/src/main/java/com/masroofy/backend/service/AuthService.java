package com.masroofy.backend.service;

import com.masroofy.backend.dto.request.EmailRequest;
import com.masroofy.backend.dto.request.LoginRequest;
import com.masroofy.backend.dto.request.RefreshTokenRequest;
import com.masroofy.backend.dto.request.RegisterRequest;
import com.masroofy.backend.dto.request.ResetPasswordRequest;
import com.masroofy.backend.dto.request.VerifyCodeRequest;
import com.masroofy.backend.dto.response.AuthTokensResponse;
import com.masroofy.backend.dto.response.CodeDispatchResponse;
import com.masroofy.backend.dto.response.EmailVerifiedResponse;
import com.masroofy.backend.dto.response.MessageResponse;
import com.masroofy.backend.dto.response.RegisterResponse;
import com.masroofy.backend.dto.response.ResetCodeVerifiedResponse;
import com.masroofy.backend.dto.response.UserResponse;
import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.FirebaseSession;
import com.masroofy.backend.model.AuthCode;
import com.masroofy.backend.model.AuthCodePurpose;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import com.masroofy.backend.service.AuthCodeService.IssuedCode;
import com.masroofy.backend.service.AuthCodeService.IssuedToken;
import com.masroofy.backend.util.EmailUtils;
import java.time.Clock;
import java.time.Duration;
import java.time.Instant;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;
import org.springframework.dao.DuplicateKeyException;
import org.springframework.stereotype.Service;
import org.springframework.transaction.support.TransactionTemplate;

/**
 * Sign-up, email verification, login, token refresh, logout and password reset.
 * Firebase Authentication owns the credentials; the database owns the profile and the one-time codes.
 */
@Service
public class AuthService {

    private static final Logger log = LoggerFactory.getLogger(AuthService.class);

    private final UserRepository userRepository;
    private final AuthCodeService authCodeService;
    private final FirebaseIdentityClient firebase;
    private final EmailService emailService;
    private final PasswordPolicy passwordPolicy;
    private final TransactionTemplate transactionTemplate;
    private final Clock clock;

    public AuthService(UserRepository userRepository, AuthCodeService authCodeService,
                       FirebaseIdentityClient firebase, EmailService emailService, PasswordPolicy passwordPolicy,
                       TransactionTemplate transactionTemplate, Clock clock) {
        this.userRepository = userRepository;
        this.authCodeService = authCodeService;
        this.firebase = firebase;
        this.emailService = emailService;
        this.passwordPolicy = passwordPolicy;
        this.transactionTemplate = transactionTemplate;
        this.clock = clock;
    }

    // ---- 01-02 Create an account ------------------------------------------------------------------------

    public RegisterResponse register(RegisterRequest request) {
        String email = EmailUtils.normalize(request.email());
        String fullName = normalizeName(request.fullName());
        passwordPolicy.validate("password", request.password(), fullName, email);

        if (userRepository.existsByEmail(email)) {
            throw new ApiException(ErrorCode.EMAIL_ALREADY_IN_USE);
        }

        String firebaseUid = firebase.createUser(email, request.password(), fullName);
        Instant now = clock.instant();
        User user = new User(UUID.randomUUID(), firebaseUid, email, null, fullName, User.DEFAULT_CURRENCY,
                User.DEFAULT_LOCALE, User.DEFAULT_TIMEZONE, null, null, now, now, now);

        IssuedCode code;
        try {
            code = transactionTemplate.execute(status -> {
                userRepository.insert(user);
                return authCodeService.issueCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION);
            });
        } catch (RuntimeException e) {
            // Keep Firebase and the database consistent: no orphaned Firebase account.
            rollbackFirebaseUser(firebaseUid);
            if (e instanceof DuplicateKeyException) {
                throw new ApiException(ErrorCode.EMAIL_ALREADY_IN_USE);
            }
            throw e;
        }

        boolean sent = trySend(() -> emailService.sendVerificationCode(email, fullName, code.code(), codeTtl()));
        return new RegisterResponse(UserResponse.from(user), dispatch(email, code.expiresAt()), sent);
    }

    // ---- 01-03 Verify signup email ----------------------------------------------------------------------

    public EmailVerifiedResponse verifyEmail(VerifyCodeRequest request) {
        String email = EmailUtils.normalize(request.email());
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException(ErrorCode.INVALID_OR_EXPIRED_CODE));
        if (user.isEmailVerified()) {
            throw new ApiException(ErrorCode.EMAIL_ALREADY_VERIFIED);
        }
        authCodeService.verifyCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION, request.code());
        markVerified(user);
        return new EmailVerifiedResponse(user.email(), true);
    }

    public CodeDispatchResponse resendVerificationCode(EmailRequest request) {
        String email = EmailUtils.normalize(request.email());
        Optional<User> found = userRepository.findByEmail(email);
        if (found.isEmpty() || found.get().isEmailVerified()) {
            // Nothing to send; answer exactly as if a code was sent.
            return genericDispatch(email);
        }
        User user = found.get();
        IssuedCode code = authCodeService.issueCode(user.id(), AuthCodePurpose.EMAIL_VERIFICATION);
        emailService.sendVerificationCode(user.email(), user.fullName(), code.code(), codeTtl());
        return dispatch(user.email(), code.expiresAt());
    }

    // ---- 01-04 Log in -----------------------------------------------------------------------------------

    public AuthTokensResponse login(LoginRequest request) {
        String email = EmailUtils.normalize(request.email());
        FirebaseSession session = firebase.signInWithPassword(email, request.password());
        User user = userRepository.findByFirebaseUid(session.uid()).orElseThrow(() -> {
            log.error("Firebase user {} has no database profile", session.uid());
            return new ApiException(ErrorCode.INVALID_CREDENTIALS);
        });
        requireVerified(user);
        return tokens(session, user);
    }

    public AuthTokensResponse refresh(RefreshTokenRequest request) {
        FirebaseSession session = firebase.refreshSession(request.refreshToken());
        User user = userRepository.findByFirebaseUid(session.uid())
                .orElseThrow(() -> new ApiException(ErrorCode.INVALID_REFRESH_TOKEN));
        requireVerified(user);
        return tokens(session, user);
    }

    /** Signs the user out on every device by revoking their Firebase refresh tokens. */
    public void logout(String firebaseUid) {
        firebase.revokeRefreshTokens(firebaseUid);
    }

    // ---- 01-05 / 01-06 / 01-07 Password reset -----------------------------------------------------------

    public CodeDispatchResponse forgotPassword(EmailRequest request) {
        String email = EmailUtils.normalize(request.email());
        Optional<User> found = userRepository.findByEmail(email);
        if (found.isEmpty()) {
            return genericDispatch(email);
        }
        User user = found.get();
        IssuedCode code = authCodeService.issueCode(user.id(), AuthCodePurpose.PASSWORD_RESET);
        emailService.sendPasswordResetCode(user.email(), user.fullName(), code.code(), codeTtl());
        return dispatch(user.email(), code.expiresAt());
    }

    public ResetCodeVerifiedResponse verifyResetCode(VerifyCodeRequest request) {
        String email = EmailUtils.normalize(request.email());
        User user = userRepository.findByEmail(email)
                .orElseThrow(() -> new ApiException(ErrorCode.INVALID_OR_EXPIRED_CODE));
        authCodeService.verifyCode(user.id(), AuthCodePurpose.PASSWORD_RESET, request.code());
        IssuedToken token = authCodeService.issueResetToken(user.id());
        return new ResetCodeVerifiedResponse(token.token(), authCodeService.secondsUntil(token.expiresAt()));
    }

    public MessageResponse resetPassword(ResetPasswordRequest request) {
        if (!request.newPassword().equals(request.confirmPassword())) {
            throw new ApiException(ErrorCode.PASSWORDS_DO_NOT_MATCH, ErrorCode.PASSWORDS_DO_NOT_MATCH.defaultMessage(),
                    Map.of(), List.of(new FieldErrorDetail("confirmPassword", "PASSWORDS_MATCH",
                            ErrorCode.PASSWORDS_DO_NOT_MATCH.defaultMessage())), null);
        }
        AuthCode resetToken = authCodeService.findActiveResetToken(request.resetToken());
        User user = userRepository.findById(resetToken.userId())
                .orElseThrow(() -> new ApiException(ErrorCode.INVALID_RESET_TOKEN));

        passwordPolicy.validate("newPassword", request.newPassword(), user.fullName(), user.email());
        rejectCurrentPassword(user, request.newPassword());

        firebase.updatePassword(user.firebaseUid(), request.newPassword());
        authCodeService.consume(resetToken);
        firebase.revokeRefreshTokens(user.firebaseUid());
        if (!user.isEmailVerified()) {
            // Receiving the reset code proves the user controls this inbox.
            markVerified(user);
        }
        return new MessageResponse("Your password has been reset successfully.");
    }

    // ---- helpers ----------------------------------------------------------------------------------------

    /**
     * "Use a password you have not used for this account before": Firebase never reveals the current password,
     * so we check by trying to sign in with the new one.
     */
    private void rejectCurrentPassword(User user, String newPassword) {
        try {
            firebase.signInWithPassword(user.email(), newPassword);
        } catch (ApiException e) {
            if (e.getErrorCode() == ErrorCode.INVALID_CREDENTIALS) {
                return;
            }
            throw e;
        }
        throw new ApiException(ErrorCode.PASSWORD_REUSED, ErrorCode.PASSWORD_REUSED.defaultMessage(), Map.of(),
                List.of(new FieldErrorDetail("newPassword", ErrorCode.PASSWORD_REUSED.name(),
                        ErrorCode.PASSWORD_REUSED.defaultMessage())), null);
    }

    private void markVerified(User user) {
        userRepository.markEmailVerified(user.id(), clock.instant());
        try {
            firebase.markEmailVerified(user.firebaseUid());
        } catch (ApiException e) {
            // The database is the source of truth for verification; Firebase's flag is informational.
            log.warn("Could not mark Firebase user {} as verified: {}", user.firebaseUid(), e.getErrorCode());
        }
    }

    private void requireVerified(User user) {
        if (!user.isEmailVerified()) {
            throw new ApiException(ErrorCode.EMAIL_NOT_VERIFIED,
                    Map.of("maskedEmail", EmailUtils.mask(user.email())));
        }
    }

    private AuthTokensResponse tokens(FirebaseSession session, User user) {
        return new AuthTokensResponse(session.idToken(), session.refreshToken(), AuthTokensResponse.BEARER,
                session.expiresInSeconds(), UserResponse.from(user));
    }

    private CodeDispatchResponse dispatch(String email, Instant expiresAt) {
        return new CodeDispatchResponse(EmailUtils.mask(email), authCodeService.codeLength(),
                authCodeService.secondsUntil(expiresAt), authCodeService.resendCooldownSeconds());
    }

    private CodeDispatchResponse genericDispatch(String email) {
        return new CodeDispatchResponse(EmailUtils.mask(email), authCodeService.codeLength(),
                authCodeService.codeTtlSeconds(), authCodeService.resendCooldownSeconds());
    }

    private Duration codeTtl() {
        return Duration.ofSeconds(authCodeService.codeTtlSeconds());
    }

    private void rollbackFirebaseUser(String firebaseUid) {
        try {
            firebase.deleteUser(firebaseUid);
        } catch (RuntimeException cleanupFailure) {
            log.error("Could not delete Firebase user {} after a failed sign-up", firebaseUid, cleanupFailure);
        }
    }

    private static boolean trySend(Runnable send) {
        try {
            send.run();
            return true;
        } catch (ApiException e) {
            log.warn("Sign-up email not sent; the user can use 'Resend code'");
            return false;
        }
    }

    private static String normalizeName(String name) {
        return name.trim().replaceAll("\\s+", " ");
    }
}
