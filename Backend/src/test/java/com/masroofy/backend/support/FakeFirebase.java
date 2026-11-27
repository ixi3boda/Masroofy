package com.masroofy.backend.support;

import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.FirebaseSession;
import com.masroofy.backend.firebase.VerifiedToken;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;

/**
 * In-memory stand-in for Firebase Authentication: users with passwords, sign-in, and ID tokens of the form
 * {@code token-for:<uid>}. Behaves like the real client for the flows the tests drive.
 */
public class FakeFirebase implements FirebaseIdentityClient {

    public record Account(String uid, String email, String password, String displayName, boolean emailVerified,
                          int sessionVersion) {
    }

    private final Map<String, Account> byUid = new ConcurrentHashMap<>();

    public Optional<Account> account(String email) {
        return byUid.values().stream().filter(a -> a.email().equals(email)).findFirst();
    }

    public void clear() {
        byUid.clear();
    }

    @Override
    public String createUser(String email, String password, String displayName) {
        if (account(email).isPresent()) {
            throw new ApiException(ErrorCode.EMAIL_ALREADY_IN_USE);
        }
        String uid = "fake-" + email;
        byUid.put(uid, new Account(uid, email, password, displayName, false, 0));
        return uid;
    }

    @Override
    public void deleteUser(String uid) {
        byUid.remove(uid);
    }

    @Override
    public Optional<String> findUidByEmail(String email) {
        return account(email).map(Account::uid);
    }

    @Override
    public void markEmailVerified(String uid) {
        byUid.computeIfPresent(uid, (k, a) -> new Account(a.uid(), a.email(), a.password(), a.displayName(), true,
                a.sessionVersion()));
    }

    @Override
    public void updatePassword(String uid, String newPassword) {
        byUid.computeIfPresent(uid, (k, a) -> new Account(a.uid(), a.email(), newPassword, a.displayName(),
                a.emailVerified(), a.sessionVersion()));
    }

    @Override
    public void revokeRefreshTokens(String uid) {
    }

    @Override
    public void setSessionVersion(String uid, int version) {
        byUid.computeIfPresent(uid, (k, a) -> new Account(a.uid(), a.email(), a.password(), a.displayName(),
                a.emailVerified(), version));
    }

    @Override
    public FirebaseSession signInWithPassword(String email, String password) {
        Account account = account(email).filter(a -> a.password().equals(password))
                .orElseThrow(() -> new ApiException(ErrorCode.INVALID_CREDENTIALS));
        return new FirebaseSession("token-for:" + account.uid(), "refresh-for:" + account.uid(), 3600, account.uid());
    }

    @Override
    public FirebaseSession refreshSession(String refreshToken) {
        String uid = refreshToken.substring("refresh-for:".length());
        return new FirebaseSession("token-for:" + uid, refreshToken, 3600, uid);
    }

    @Override
    public VerifiedToken verifyIdToken(String idToken, boolean checkRevoked) {
        if (idToken == null || !idToken.startsWith("token-for:")) {
            throw new ApiException(ErrorCode.UNAUTHORIZED);
        }
        Account account = byUid.get(idToken.substring("token-for:".length()));
        if (account == null) {
            throw new ApiException(ErrorCode.UNAUTHORIZED);
        }
        return new VerifiedToken(account.uid(), account.email(), account.sessionVersion());
    }
}
