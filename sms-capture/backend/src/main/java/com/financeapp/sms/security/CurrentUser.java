package com.financeapp.sms.security;

import org.springframework.http.HttpStatus;
import org.springframework.security.core.Authentication;
import org.springframework.security.core.context.SecurityContextHolder;
import org.springframework.stereotype.Component;
import org.springframework.web.server.ResponseStatusException;

/**
 * Returns the signed-in user's id. ADAPT THIS to your authentication: here it assumes your JWT filter sets
 * the authentication name to the numeric user id. Every SMS query is filtered by this id, so each person
 * sees only their own records.
 */
@Component
public class CurrentUser {
    public Long id() {
        Authentication auth = SecurityContextHolder.getContext().getAuthentication();
        if (auth == null || !auth.isAuthenticated() || auth.getName() == null) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "not signed in");
        }
        try {
            return Long.valueOf(auth.getName());
        } catch (NumberFormatException e) {
            throw new ResponseStatusException(HttpStatus.UNAUTHORIZED, "unexpected principal; adapt CurrentUser.id()");
        }
    }
}
