package com.financeapp.sms;

import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;

/**
 * Runs on the phone before anything is uploaded. Pure Java (no Android classes) so it is unit-testable.
 *  - only SMS from senders on the allow-list (banks/wallets) are considered: personal SMS never leave the phone;
 *  - one-time passwords are dropped on the phone, so codes are never sent to or stored on the server.
 */
public final class SmsFilter {
    private SmsFilter() {}

    /** Same rule as the backend's SenderRegistry.normalize: lower case, letters and digits only. */
    public static String normalizeSender(String sender) {
        if (sender == null) return "";
        StringBuilder b = new StringBuilder();
        for (char c : sender.toLowerCase(Locale.ROOT).toCharArray()) if (Character.isLetterOrDigit(c)) b.append(c);
        return b.toString();
    }

    public static boolean isAllowedSender(String sender, Set<String> normalizedAllowList) {
        String s = normalizeSender(sender);
        return !s.isEmpty() && normalizedAllowList.contains(s);
    }

    /** Phrases that only appear in one-time-password messages (not generic "do not share" footers). */
    private static final Pattern OTP_WORDS = Pattern.compile(
            "\\bOTP\\b|one[- ]time (?:password|code|passcode)|verification code|login code|payment code|activation code|"
          + "security code|passcode|رمز التحقق|رمز التفعيل|رمز الدخول|كود التحقق|كود التأكيد|كود التفعيل|كود الدخول|كود الدفع|"
          + "كلمة السر المؤقتة|كلمة المرور المؤقتة|الرقم السري المؤقت|لمرة واحدة",
            Pattern.CASE_INSENSITIVE | Pattern.UNICODE_CASE | Pattern.UNICODE_CHARACTER_CLASS);
    /**
     * A 4-8 digit code, possibly spaced ("90 41 77"). Excludes numbers that belong to something else: amounts
     * (1,250.50, "EGP 1500", "1500 جنيه"), dates and times (12/11/2026, 14:05), card endings (****4421, xx4421).
     */
    private static final Pattern CODE = Pattern.compile(
            "(?<![\\d.,/:*#xX٬٫\\-])(?<!(?:EGP|LE|USD)\\s?)"
          + "(?:[0-9٠-٩]{4,8}|[0-9٠-٩]{2,3}(?: [0-9٠-٩]{2,3}){1,3})"
          + "(?![\\d,٬٫/:\\-]|[.][0-9٠-٩])(?!\\s?(?:EGP|LE|USD|جنيه|جنية|ج\\.م))");
    private static final int NEAR = 30;

    /**
     * True for one-time-password messages: an OTP phrase with a code within 30 characters of it.
     * A transaction alert that merely ends with "never share your OTP" has no code next to the phrase, so it is kept.
     * Such OTP messages are never uploaded.
     */
    public static boolean looksLikeOtp(String body) {
        if (body == null) return false;
        java.util.regex.Matcher k = OTP_WORDS.matcher(body);
        while (k.find()) {
            // Search only near the phrase, but let the pattern see the characters around the window
            // (otherwise "****4421" cut to "4421" would look like a code).
            java.util.regex.Matcher c = CODE.matcher(body)
                    .region(Math.max(0, k.start() - NEAR), Math.min(body.length(), k.end() + NEAR))
                    .useTransparentBounds(true).useAnchoringBounds(false);
            if (c.find()) return true;
        }
        return false;
    }
}
