package com.masroofy.backend.util;

import java.util.Locale;

public final class EmailUtils {

    /**
     * Stricter than {@code @Email} alone: the domain must contain a dot ("user@localhost" is rejected),
     * which matches what Firebase Authentication accepts.
     */
    public static final String VALID_EMAIL_REGEX = "^[^@\\s]+@[^@\\s]+\\.[^@\\s]{2,}$";

    private EmailUtils() {
    }

    /** Removes the spaces phone keyboards add around typed text. */
    public static String trim(String value) {
        return value == null ? null : value.trim();
    }

    /** Emails are compared and stored trimmed and lower-cased, matching Firebase's case-insensitive emails. */
    public static String normalize(String email) {
        return email == null ? null : email.trim().toLowerCase(Locale.ROOT);
    }

    /** "mariam@example.com" becomes "m***@example.com", as shown on the verification screens. */
    public static String mask(String email) {
        if (email == null) {
            return null;
        }
        int at = email.indexOf('@');
        if (at <= 0) {
            return "***";
        }
        return email.charAt(0) + "***" + email.substring(at);
    }
}
