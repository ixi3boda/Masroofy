package com.masroofy.backend.service;

import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.springframework.stereotype.Component;

/**
 * The password requirements shown on screens 01-02 and 01-07: at least 8 characters (at most 128), a number or
 * symbol, and an uppercase letter. (The common-password and name/email checks were removed on purpose.)
 */
@Component
public class PasswordPolicy {

    public static final int MIN_LENGTH = 8;
    public static final int MAX_LENGTH = 128;

    public enum Rule {
        MIN_LENGTH("Use at least 8 characters"),
        MAX_LENGTH("Use at most 128 characters"),
        NUMBER_OR_SYMBOL("Include a number or symbol"),
        UPPERCASE("Include an uppercase letter");

        private final String message;

        Rule(String message) {
            this.message = message;
        }

        public String message() {
            return message;
        }
    }

    /** Returns the rules the password breaks; empty when it is acceptable. */
    public List<Rule> check(String password) {
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
        if (value.codePoints().noneMatch(PasswordPolicy::isUppercase)) {
            failed.add(Rule.UPPERCASE);
        }
        return failed;
    }

    /** Throws {@link ErrorCode#WEAK_PASSWORD} listing every broken rule against {@code field}. */
    public void validate(String field, String password) {
        List<Rule> failed = check(password);
        if (failed.isEmpty()) {
            return;
        }
        List<FieldErrorDetail> errors = failed.stream()
                .map(rule -> new FieldErrorDetail(field, rule.name(), rule.message()))
                .toList();
        throw new ApiException(ErrorCode.WEAK_PASSWORD, ErrorCode.WEAK_PASSWORD.defaultMessage(),
                Map.of("failedRules", failed.stream().map(Rule::name).toList()), errors, null);
    }

    /** An uppercase letter in any alphabet (Unicode category Lu), the same test as the app's {@code \p{Lu}}. */
    private static boolean isUppercase(int codePoint) {
        return Character.getType(codePoint) == Character.UPPERCASE_LETTER;
    }

    private static boolean isSymbol(int c) {
        return !Character.isLetterOrDigit(c) && !Character.isWhitespace(c);
    }
}
