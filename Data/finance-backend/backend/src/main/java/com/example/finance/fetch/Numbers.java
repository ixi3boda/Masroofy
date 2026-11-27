package com.example.finance.fetch;

final class Numbers {
    private Numbers() {}

    /** "6,857.50" -> 6857.5; returns null for text that is not a number. */
    static Double parse(Object value) {
        if (value == null) return null;
        if (value instanceof Number n) return n.doubleValue();
        String s = value.toString().replace(",", "").trim();
        if (s.isEmpty()) return null;
        try {
            return Double.parseDouble(s);
        } catch (NumberFormatException e) {
            return null;
        }
    }
}
