package com.masroofy.common;

import org.springframework.stereotype.Component;

/**
 * Who is making the request. Every transaction is saved with this id and users only see their own.
 *
 * There is no login yet, so this returns null and all transactions are shared. When you add
 * Spring Security (JWT), return the logged-in user's id here, for example:
 *   return SecurityContextHolder.getContext().getAuthentication().getName();
 * Nothing else needs to change.
 */
@Component
public class CurrentUser {

    public String id() {
        return null;
    }
}
