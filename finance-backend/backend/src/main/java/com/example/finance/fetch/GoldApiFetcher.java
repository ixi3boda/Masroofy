package com.example.finance.fetch;

import java.io.IOException;
import java.time.Instant;
import java.util.Map;
import org.jsoup.Connection;
import org.springframework.stereotype.Component;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.json.JsonMapper;

/**
 * World gold and silver prices in US$ per troy ounce from gold-api.com (free, no key):
 * https://api.gold-api.com/price/XAU (gold) and https://api.gold-api.com/price/XAG (silver).
 */
@Component
public class GoldApiFetcher {
    static final String URL = "https://api.gold-api.com/price/";

    /** Price in US$ per ounce, and when gold-api.com last updated it. */
    public record Quote(double usd, Instant updatedAt) { }

    private final JsonMapper json;

    public GoldApiFetcher(JsonMapper json) {
        this.json = json;
    }

    public Quote gold() throws IOException {
        return fetch("XAU");
    }

    public Quote silver() throws IOException {
        return fetch("XAG");
    }

    private Quote fetch(String symbol) throws IOException {
        Connection.Response r = Http.connect(URL + symbol).header("Accept", "application/json")
                .ignoreHttpErrors(true).execute();
        if (r.statusCode() != 200) {
            String b = r.body().replaceAll("\\s+", " ");
            throw new IOException("gold-api.com " + symbol + " answered " + r.statusCode() + ": "
                    + b.substring(0, Math.min(150, b.length())));
        }
        return parse(r.body(), symbol);
    }

    /** {"currency":"USD","name":"Gold","price":3539.0,"symbol":"XAU","updatedAt":"2026-11-22T02:24:09Z",...} */
    Quote parse(String body, String symbol) throws IOException {
        Map<String, Object> m = json.readValue(body, new TypeReference<Map<String, Object>>() { });
        Double price = Numbers.parse(m.get("price"));
        if (price == null || price <= 0) throw new IOException("gold-api.com " + symbol + ": no price in " + body);
        if (m.get("currency") != null && !"USD".equals(m.get("currency"))) {
            throw new IOException("gold-api.com " + symbol + ": price is in " + m.get("currency") + ", not USD");
        }
        Instant at;
        try {
            at = Instant.parse(String.valueOf(m.get("updatedAt")));
        } catch (RuntimeException e) {
            at = Instant.now();
        }
        return new Quote(price, at);
    }
}
