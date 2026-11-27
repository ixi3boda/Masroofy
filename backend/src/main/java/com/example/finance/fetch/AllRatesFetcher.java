package com.example.finance.fetch;

import com.example.finance.model.FxRate;
import java.io.IOException;
import java.time.Instant;
import java.time.LocalDate;
import java.time.ZoneId;
import java.time.format.DateTimeParseException;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import org.jsoup.Connection;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/**
 * Exchange rates for every currency in the AllRatesToday daily reference rate, from
 * {@code https://allratestoday.com/api/open/reference-rate} (free, no key).
 *
 * <p>The answer is one table per day, sampled at 16:00 London, with USD as the base:
 * <pre>
 * {"rate_date":"2026-11-26","time":"16:00 London","base":"USD","published_at":"2026-11-26T16:02:26.847Z",
 *  "rates":[{"base":"USD","quote":"EGP","value":54.8438},{"base":"USD","quote":"EUR","value":0.911245},...]}
 * </pre>
 * Each value is units of the quote currency for 1 USD, so EGP per 1 unit of X = value(EGP) / value(X),
 * and USD itself = value(EGP). It is a single median reference rate (no buy/sell spread), so
 * {@code buy} and {@code sell} are the same number.
 * Terms: public pages that show the rates need a visible link to allratestoday.com.
 */
@Component
public class AllRatesFetcher {
    public static final String SOURCE = "allratestoday";

    /** Rates are saved with 8 decimals, enough for currencies worth a fraction of a piastre. */
    private static final double SCALE = 1e8;

    private final JsonMapper json;
    private final String url;
    private final ZoneId zone;

    public AllRatesFetcher(JsonMapper json,
                           @Value("${app.fx.allrates-url}") String url,
                           @Value("${app.update.zone}") ZoneId zone) {
        this.json = json;
        this.url = url;
        this.zone = zone;
    }

    public List<FxRate> fetch() throws IOException {
        Connection.Response r = Http.connect(url).header("Accept", "application/json")
                .ignoreHttpErrors(true).execute();
        if (r.statusCode() != 200) {
            String b = r.body() == null ? "" : r.body().replaceAll("\\s+", " ");
            throw new IOException("AllRatesToday answered " + r.statusCode() + ": "
                    + b.substring(0, Math.min(150, b.length())));
        }
        return parse(r.body());
    }

    /** Turns the reference-rate table into EGP per 1 unit of every other currency. */
    List<FxRate> parse(String body) throws IOException {
        Map<String, Object> answer = json.readValue(body, new TypeReference<Map<String, Object>>() { });
        if (!(answer.get("rates") instanceof List<?> rates)) {
            throw new IOException("AllRatesToday answer has no rates");
        }
        String base = code(answer.get("base"));

        // quote currency -> units of it for 1 unit of the base currency
        Map<String, Double> perBase = new LinkedHashMap<>();
        for (Object o : rates) {
            if (!(o instanceof Map<?, ?> row)) continue;
            String rowBase = row.get("base") != null ? code(row.get("base")) : base;
            if (base == null) base = rowBase;
            if (rowBase == null || !rowBase.equals(base)) continue;
            String quote = code(row.get("quote"));
            Double value = Numbers.parse(row.get("value"));
            if (quote == null || value == null || value <= 0) continue;
            perBase.put(quote, value);
        }
        if (base == null) throw new IOException("AllRatesToday answer has no base currency");
        perBase.putIfAbsent(base, 1.0);
        Double egpPerBase = perBase.get("EGP");
        if (egpPerBase == null) throw new IOException("AllRatesToday answer has no rates for EGP");

        LocalDate date = date(answer);
        List<FxRate> out = new ArrayList<>();
        for (Map.Entry<String, Double> e : perBase.entrySet()) {
            if (e.getKey().equals("EGP")) continue;
            double egp = Math.round(egpPerBase / e.getValue() * SCALE) / SCALE;  // EGP for 1 unit
            FxRate fx = new FxRate(date, e.getKey(), egp, egp);
            fx.source = SOURCE;
            out.add(fx);
        }
        return out;
    }

    /** "rate_date" (the day the table is for), else the Cairo date of "published_at", else today. */
    private LocalDate date(Map<String, Object> answer) {
        Object rateDate = answer.get("rate_date");
        if (rateDate != null) {
            try {
                return LocalDate.parse(rateDate.toString().trim().substring(0, 10));
            } catch (RuntimeException ignored) { }
        }
        Object published = answer.get("published_at");
        if (published != null) {
            try {
                return LocalDate.ofInstant(Instant.parse(published.toString().trim()), zone);
            } catch (DateTimeParseException ignored) { }
        }
        return LocalDate.now(zone);
    }

    /** A 3-letter currency code in capitals, or null. */
    private static String code(Object raw) {
        if (raw == null) return null;
        String c = raw.toString().trim().toUpperCase(Locale.ROOT);
        return c.matches("[A-Z]{3}") ? c : null;
    }
}
