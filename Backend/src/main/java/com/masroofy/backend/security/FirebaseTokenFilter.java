package com.masroofy.backend.security;

import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.firebase.FirebaseIdentityClient;
import com.masroofy.backend.firebase.VerifiedToken;
import com.masroofy.backend.model.User;
import com.masroofy.backend.repository.UserRepository;
import jakarta.servlet.FilterChain;
import jakarta.servlet.ServletException;
import jakarta.servlet.http.HttpServletRequest;
import jakarta.servlet.http.HttpServletResponse;
import java.io.IOException;
import java.util.List;
import java.util.Optional;
import org.springframework.http.HttpHeaders;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.authority.SimpleGrantedAuthority;
import org.springframework.security.core.context.SecurityContext;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.security.web.authentication.WebAuthenticationDetailsSource;
import org.springframework.security.web.util.matcher.RequestMatcher;
import org.springframework.web.filter.OncePerRequestFilter;

/**
 * Authenticates {@code Authorization: Bearer <Firebase ID token>} requests. Verified users get ROLE_USER;
 * users who have not verified their email get only ROLE_UNVERIFIED and cannot reach the app's data.
 */
public class FirebaseTokenFilter extends OncePerRequestFilter {

    public static final String ROLE_USER = "ROLE_USER";
    public static final String ROLE_UNVERIFIED = "ROLE_UNVERIFIED";
    private static final String BEARER_PREFIX = "Bearer ";

    private final FirebaseIdentityClient firebase;
    private final UserRepository userRepository;
    private final ErrorResponseWriter errorWriter;
    private final RequestMatcher publicEndpoints;
    private final boolean checkRevoked;

    public FirebaseTokenFilter(FirebaseIdentityClient firebase, UserRepository userRepository,
                               ErrorResponseWriter errorWriter, RequestMatcher publicEndpoints,
                               boolean checkRevoked) {
        this.firebase = firebase;
        this.userRepository = userRepository;
        this.errorWriter = errorWriter;
        this.publicEndpoints = publicEndpoints;
        this.checkRevoked = checkRevoked;
    }

    @Override
    protected boolean shouldNotFilter(HttpServletRequest request) {
        // A stale token sent to /login or /register must not block the request.
        return publicEndpoints.matches(request);
    }

    @Override
    protected void doFilterInternal(HttpServletRequest request, HttpServletResponse response, FilterChain chain)
            throws ServletException, IOException {
        String header = request.getHeader(HttpHeaders.AUTHORIZATION);
        if (header == null || header.isBlank()) {
            chain.doFilter(request, response);
            return;
        }
        if (!header.regionMatches(true, 0, BEARER_PREFIX, 0, BEARER_PREFIX.length())
                || header.substring(BEARER_PREFIX.length()).isBlank()) {
            errorWriter.write(request, response, ErrorCode.UNAUTHORIZED, "Use 'Authorization: Bearer <token>'.");
            return;
        }
        String token = header.substring(BEARER_PREFIX.length()).trim();

        VerifiedToken verified;
        try {
            verified = firebase.verifyIdToken(token, checkRevoked);
        } catch (ApiException e) {
            errorWriter.write(request, response, e.getErrorCode(), e.getMessage());
            return;
        }

        Optional<User> user = userRepository.findByFirebaseUid(verified.uid());
        if (user.isEmpty()) {
            errorWriter.write(request, response, ErrorCode.UNAUTHORIZED, "No Masroofy account for this token.");
            return;
        }

        User account = user.get();
        AuthenticatedUser principal = new AuthenticatedUser(account.id(), account.firebaseUid(), account.email(),
                account.isEmailVerified());
        String role = account.isEmailVerified() ? ROLE_USER : ROLE_UNVERIFIED;
        UsernamePasswordAuthenticationToken authentication = new UsernamePasswordAuthenticationToken(
                principal, null, List.of(new SimpleGrantedAuthority(role)));
        authentication.setDetails(new WebAuthenticationDetailsSource().buildDetails(request));

        SecurityContext context = SecurityContextHolder.createEmptyContext();
        context.setAuthentication(authentication);
        SecurityContextHolder.setContext(context);
        chain.doFilter(request, response);
    }
}
