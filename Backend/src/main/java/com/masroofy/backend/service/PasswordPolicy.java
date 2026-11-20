package com.masroofy.backend.service;

import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * The password requirements shown on screens 01-02 and 01-07:
 * at least 8 characters, a number or symbol, and not containing the user's name or email.
 */
@Component
public class PasswordPolicy {

    public static final int MIN_LENGTH = 8;
    public static final int MAX_LENGTH = 128;
    /** Name parts / email parts shorter than this are too common to reject on. */
    private static final int MIN_PERSONAL_TOKEN_LENGTH = 3;

    public enum Rule {
        MIN_LENGTH("Use at least 8 characters"),
        MAX_LENGTH("Use at most 128 characters"),
        NUMBER_OR_SYMBOL("Include a number or symbol"),
        NO_PERSONAL_INFO("Do not include your name or email");

        private final String message;

        Rule(String message) {
            this.message = message;
        }

        public String message() {
            return message;
        }
    }

    /** Returns the rules the password breaks; empty when it is acceptable. */
    public List<Rule> check(String password, String fullName, String email) {
        List<Rule> failed = new ArrayList<>();
        String value = password == null ? "" : password;
        if (value.length() < MIN_LENGTH) {
            failed.add(Rule.MIN_LENGTH);
        }
        if (value.length() > MAX_LENGTH) {
            failed.add(Rule.MAX_LENGTH);
        }
        if (value.chars().noneMatch(c -> Character.isDigit(c) || isSymbol(c))) {
            failed.add(Rule.NUMBER_OR_SYMBOL);
        }
        if (containsPersonalInfo(value, fullName, email)) {
            failed.add(Rule.NO_PERSONAL_INFO);
        }
        return failed;
    }

    /** Throws {@link ErrorCode#WEAK_PASSWORD} listing every broken rule against {@code field}. */
    public void validate(String field, String password, String fullName, String email) {
        List<Rule> failed = check(password, fullName, email);
        if (failed.isEmpty()) {
            return;
        }
        List<FieldErrorDetail> errors = failed.stream()
                .map(rule -> new FieldErrorDetail(field, rule.name(), rule.message()))
                .toList();
        throw new ApiException(ErrorCode.WEAK_PASSWORD, ErrorCode.WEAK_PASSWORD.defaultMessage(),
                Map.of("failedRules", failed.stream().map(Rule::name).toList()), errors, null);
    }

    private static boolean isSymbol(int c) {
        return !Character.isLetterOrDigit(c) && !Character.isWhitespace(c);
    }

    private static boolean containsPersonalInfo(String password, String fullName, String email) {
        String lowered = password.toLowerCase(Locale.ROOT);
        for (String token : personalTokens(fullName, email)) {
            if (lowered.contains(token)) {
                return true;
            }
        }
        return false;
    }

    private static List<String> personalTokens(String fullName, String email) {
        List<String> tokens = new ArrayList<>();
        if (fullName != null) {
            for (String part : fullName.toLowerCase(Locale.ROOT).split("\\s+")) {
                addToken(tokens, part);
            }
        }
        if (email != null) {
            String lowered = email.toLowerCase(Locale.ROOT).trim();
            int at = lowered.indexOf('@');
            String local = at >= 0 ? lowered.substring(0, at) : lowered;
            addToken(tokens, local);
            for (String part : local.split("[._+\\-]+")) {
                addToken(tokens, part);
            }
        }
        return tokens;
    }

    private static void addToken(List<String> tokens, String token) {
        if (token != null && token.length() >= MIN_PERSONAL_TOKEN_LENGTH) {
            tokens.add(token);
        }
    }
}
