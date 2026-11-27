package com.example.finance.fetch;

import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.format.DateTimeParseException;
import java.util.List;
import java.util.Locale;

/** Reads the date formats the sources use ("20/11/2026", "2026-11-20T00:00:00", "20 Nov 2026", ...). */
final class Dates {
    private static final List<DateTimeFormatter> DAY_FIRST = formats("d/M/yyyy", "d-M-yyyy", "d.M.yyyy");
    private static final List<DateTimeFormatter> MONTH_FIRST = formats("M/d/yyyy", "M-d-yyyy");
    private static final List<DateTimeFormatter> NAMED = formats(
            "d MMM yyyy", "d MMMM yyyy", "MMM d, yyyy", "MMMM d, yyyy", "d-MMM-yyyy");

    private Dates() {}

    static LocalDate parse(String raw, boolean dayFirst) {
        String s = raw.trim();
        if (s.matches("\\d{4}-\\d{2}-\\d{2}.*")) {          // ISO, maybe with a time
            return LocalDate.parse(s.substring(0, 10));
        }
        String dateOnly = s.split("[ T]")[0];                // drop a time after a numeric date
        for (DateTimeFormatter f : dayFirst ? concat(DAY_FIRST, MONTH_FIRST) : concat(MONTH_FIRST, DAY_FIRST)) {
            try { return LocalDate.parse(dateOnly, f); } catch (DateTimeParseException ignored) { }
        }
        for (DateTimeFormatter f : NAMED) {
            try { return LocalDate.parse(s, f); } catch (DateTimeParseException ignored) { }
        }
        try { return LocalDateTime.parse(s).toLocalDate(); } catch (DateTimeParseException ignored) { }
        throw new IllegalArgumentException("Unknown date format: " + raw);
    }

    private static List<DateTimeFormatter> formats(String... patterns) {
        return java.util.Arrays.stream(patterns).map(p -> DateTimeFormatter.ofPattern(p, Locale.ENGLISH)).toList();
    }

    private static <T> List<T> concat(List<T> a, List<T> b) {
        return java.util.stream.Stream.concat(a.stream(), b.stream()).toList();
    }
}
