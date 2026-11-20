package com.masroofy.backend.service;

import com.masroofy.backend.exception.ApiException;
import com.masroofy.backend.exception.ErrorCode;
import com.masroofy.backend.exception.FieldErrorDetail;
import java.io.BufferedReader;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.UncheckedIOException;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import org.springframework.stereotype.Component;

/**
 * The password requirements shown on screens 01-02 and 01-07:
 * at least 8 characters, a number or symbol, not containing the user's name or email, and not a common or
 * easily guessed password.
 */
@Component
public class PasswordPolicy {

    public static final int MIN_LENGTH = 8;
    public static final int MAX_LENGTH = 128;
    /** Name parts / email parts shorter than this are too common to reject on. */
    private static final int MIN_PERSONAL_TOKEN_LENGTH = 3;
    private static final String COMMON_PASSWORDS = "/security/common-passwords.txt";
    private static final List<String> KEYBOARD_ROWS = List.of(
            "1234567890", "qwertyuiop", "asdfghjkl", "zxcvbnm", "qwertyuiopasdfghjklzxcvbnm", "1qaz2wsx3edc4rfv");

    private final Set<String> commonPasswords;

    public PasswordPolicy() {
        this.commonPasswords = loadCommonPasswords();
    }

    public enum Rule {
        MIN_LENGTH("Use at least 8 characters"),
        MAX_LENGTH("Use at most 128 characters"),
        NUMBER_OR_SYMBOL("Include a number or symbol"),
        NO_PERSONAL_INFO("Do not include your name or email"),
        COMMON_PASSWORD("Avoid common or easily guessed passwords");

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
        // Only for passwords long enough to be accepted otherwise; short ones already fail MIN_LENGTH.
        if (value.length() >= MIN_LENGTH && isCommon(value)) {
            failed.add(Rule.COMMON_PASSWORD);
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

    /**
     * A listed password (exactly, or followed by digits/symbols such as "password1!"), a single repeated character
     * ("!!!!!!!!"), a straight sequence ("12345678", "abcdefgh", "87654321") or a run along a keyboard row.
     */
    boolean isCommon(String password) {
        String lowered = password.toLowerCase(Locale.ROOT);
        if (commonPasswords.contains(lowered)) {
            return true;
        }
        String base = lowered.replaceAll("[^\\p{L}]+$", "");
        if (base.length() >= 4 && commonPasswords.contains(base)) {
            return true;
        }
        if (lowered.chars().distinct().count() == 1 || isStraightSequence(lowered)) {
            return true;
        }
        for (String row : KEYBOARD_ROWS) {
            if (row.contains(lowered) || new StringBuilder(row).reverse().toString().contains(lowered)) {
                return true;
            }
        }
        return false;
    }

    private static boolean isStraightSequence(String value) {
        int step = value.charAt(1) - value.charAt(0);
        if (Math.abs(step) != 1) {
            return false;
        }
        for (int i = 2; i < value.length(); i++) {
            if (value.charAt(i) - value.charAt(i - 1) != step) {
                return false;
            }
        }
        return true;
    }

    private static Set<String> loadCommonPasswords() {
        Set<String> words = new HashSet<>();
        try (InputStream in = PasswordPolicy.class.getResourceAsStream(COMMON_PASSWORDS)) {
            if (in == null) {
                throw new IllegalStateException(COMMON_PASSWORDS + " is missing from the classpath");
            }
            BufferedReader reader = new BufferedReader(new InputStreamReader(in, StandardCharsets.UTF_8));
            String line;
            while ((line = reader.readLine()) != null) {
                String word = line.strip().toLowerCase(Locale.ROOT);
                if (!word.isEmpty() && !word.startsWith("#")) {
                    words.add(word);
                }
            }
        } catch (IOException e) {
            throw new UncheckedIOException(e);
        }
        return Set.copyOf(words);
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
